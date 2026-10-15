"""Create a CPU-only synthetic-data bundle for local plumbing tests.

The output is deliberately a PLUMBING MODEL, not a vulnerability detector.
It uses the tiny random encoder from the smoke test and never downloads a
Hugging Face checkpoint.
"""
from __future__ import annotations

import json
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ARTIFACTS = REPO / "codesentinel_model" / "artifacts"
VERSION = "demo-synthetic-0.1"


def build_local_tokenizer(output: Path) -> None:
    """Write a self-contained tokenizer matching the random model's vocab size."""
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from tokenizers.pre_tokenizers import Whitespace

    vocab = {"[PAD]": 0, "[UNK]": 1, "[CLS]": 2, "[SEP]": 3, "[MASK]": 4}
    vocab.update({f"token_{index}": index for index in range(5, 5000)})
    tokenizer = Tokenizer(WordLevel(vocab=vocab, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = Whitespace()
    output.mkdir(parents=True, exist_ok=True)
    tokenizer.save(str(output / "tokenizer.json"))
    # These standard Hugging Face files let AutoTokenizer load the local
    # tokenizers JSON without contacting the Hub.
    (output / "tokenizer_config.json").write_text(json.dumps({"tokenizer_class": "PreTrainedTokenizerFast", "model_max_length": 512, "unk_token": "[UNK]", "pad_token": "[PAD]", "cls_token": "[CLS]", "sep_token": "[SEP]", "mask_token": "[MASK]"}), encoding="utf-8")
    (output / "special_tokens_map.json").write_text(json.dumps({"unk_token": "[UNK]", "pad_token": "[PAD]", "cls_token": "[CLS]", "sep_token": "[SEP]", "mask_token": "[MASK]"}), encoding="utf-8")


def write_smoke_config(path: Path, processed: Path, work: Path) -> None:
    path.write_text(
        f"""model:
  base_model: demo-random-roberta
  max_seq_length: 32
  num_cwe_classes: 3
  severity_levels: [low, medium, high, critical]
  dropout: 0.1
data:
  processed_dir: {processed.as_posix()}
  augment_train: true
  augment_frac: 0.2
training:
  epochs: 1
  batch_size: 4
  learning_rate: 2.0e-4
  weight_decay: 0.01
  warmup_ratio: 0.06
  seed: 0
  k_folds: 2
  loss: {{type: focal, focal_gamma: 2.0}}
  early_stopping_patience: 1
  gradient_accumulation_steps: 1
  fp16: false
calibration: {{method: temperature_scaling, fit_on: val}}
mlflow:
  tracking_uri: {work.joinpath('mlruns').as_posix()}
  experiment_name: demo-synthetic
  registered_model_name: demo-synthetic
output:
  checkpoint_dir: {work.joinpath('checkpoints').as_posix()}
  final_model_dir: {work.joinpath('final_model').as_posix()}
""",
        encoding="utf-8",
    )


def run(*args: str | Path) -> None:
    subprocess.run([sys.executable, *map(str, args)], cwd=REPO, check=True)


def build_constant_onnx(output: Path) -> None:
    """Last-resort serving artifact when this host cannot load PyTorch.

    It intentionally has fixed logits. This is only enough to exercise the
    serving contract and is more explicit than silently shipping a bad export.
    """
    import numpy as np
    import onnx
    from onnx import TensorProto, helper, numpy_helper

    outputs = {
        "vuln_logits": np.array([[0.0, 1.0]], dtype=np.float32),
        "severity_logits": np.array([[0.0, 0.0, 1.0, 0.0]], dtype=np.float32),
        "cwe_logits": np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32),
    }
    nodes = [helper.make_node("Constant", [], [name], value=numpy_helper.from_array(value)) for name, value in outputs.items()]
    graph = helper.make_graph(
        nodes,
        "codesentinel-demo-constant",
        [helper.make_tensor_value_info("input_ids", TensorProto.INT64, [1, "sequence"]), helper.make_tensor_value_info("attention_mask", TensorProto.INT64, [1, "sequence"])],
        [helper.make_tensor_value_info("vuln_logits", TensorProto.FLOAT, [1, 2]), helper.make_tensor_value_info("severity_logits", TensorProto.FLOAT, [1, 4]), helper.make_tensor_value_info("cwe_logits", TensorProto.FLOAT, [1, 4])],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 9
    onnx.checker.check_model(model)
    onnx.save(model, output)


def main() -> None:
    work = REPO / ".demo_build"
    if work.exists():
        shutil.rmtree(work)
    processed = work / "processed"
    processed.mkdir(parents=True)

    # Reuse the tiny synthetic source and repo-level split from the smoke test.
    smoke = runpy.run_path(str(REPO / "tests" / "test_smoke_pipeline.py"))
    sys.path.insert(0, str(REPO / "data"))
    from dedup_split import dedup, repo_level_split, write_jsonl
    from schema import CodeSample

    samples = [CodeSample(**row) for row in smoke["make_synthetic_dataset"](40)]
    train, val, test = repo_level_split(dedup(samples)[0], test_frac=0.2, val_frac=0.2, seed=0)
    for name, split in (("train", train), ("val", val), ("test", test)):
        write_jsonl(split, processed / f"{name}.jsonl")

    config = work / "config.yaml"
    write_smoke_config(config, processed, work)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    try:
        run(REPO / "training" / "train.py", "--config", config, "--smoke-test")
        checkpoint = work / "final_model" / "model.pt"
        run(REPO / "export" / "export_onnx.py", "--checkpoint", checkpoint, "--config", config, "--out", ARTIFACTS / "model.onnx", "--smoke-test")
        run(REPO / "export" / "export_torchscript.py", "--checkpoint", checkpoint, "--config", config, "--out", ARTIFACTS / "model_ts.pt", "--smoke-test")
        run(REPO / "export" / "parity_check.py", "--pytorch-model", checkpoint, "--onnx-model", ARTIFACTS / "model.onnx", "--torchscript-model", ARTIFACTS / "model_ts.pt", "--config", config, "--smoke-test", "--include-padding")
    except subprocess.CalledProcessError:
        build_constant_onnx(ARTIFACTS / "model.onnx")
        print("FALLBACK: PyTorch smoke training/export could not run on this host; created a fixed-logit ONNX plumbing artifact. TorchScript and parity are not available.")
    build_local_tokenizer(ARTIFACTS / "tokenizer")
    (ARTIFACTS / "cwe_vocab.json").write_text(json.dumps({"CWE-119": 0, "CWE-79": 1, "CWE-89": 2}, indent=2), encoding="utf-8")
    (ARTIFACTS / "model_version.json").write_text(json.dumps({"model_version": VERSION, "warning": "PLUMBING MODEL ONLY: tiny synthetic data and a random encoder; not a vulnerability detector."}, indent=2), encoding="utf-8")
    print(f"Built {VERSION} at {ARTIFACTS}")
    print("PLUMBING MODEL ONLY. No Hugging Face download was used; do not use this for security decisions.")


if __name__ == "__main__":
    main()
