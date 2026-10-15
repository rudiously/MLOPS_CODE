"""
Benchmarks inference latency/throughput for PyTorch, ONNX, and TorchScript,
on CPU (and GPU if available) — so Person 2 can pick the right export format
for the serving latency budget of the GitHub Action / FastAPI service.

Usage:
    python export/benchmark.py --pytorch-model training/final_model/model.pt \
        --onnx-model export/artifacts/model.onnx \
        --torchscript-model export/artifacts/model_ts.pt \
        --config training/config.yaml --n-runs 50
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
from model import CodeSentinelModel  # noqa: E402


def timeit(fn, n_runs: int, warmup: int = 5) -> dict:
    for _ in range(warmup):
        fn()
    start = time.perf_counter()
    for _ in range(n_runs):
        fn()
    elapsed = time.perf_counter() - start
    return {
        "total_seconds": elapsed,
        "mean_latency_ms": (elapsed / n_runs) * 1000,
        "throughput_per_sec": n_runs / elapsed,
    }


def benchmark_pytorch(model, input_ids, attention_mask, n_runs: int) -> dict:
    model.eval()

    def run():
        with torch.no_grad():
            model(input_ids, attention_mask)

    return timeit(run, n_runs)


def benchmark_onnx(onnx_path: Path, input_ids, attention_mask, n_runs: int) -> dict:
    import onnxruntime as ort

    session = ort.InferenceSession(str(onnx_path))
    inputs = {"input_ids": input_ids.numpy(), "attention_mask": attention_mask.numpy()}

    def run():
        session.run(None, inputs)

    return timeit(run, n_runs)


def benchmark_torchscript(ts_path: Path, input_ids, attention_mask, n_runs: int) -> dict:
    model = torch.jit.load(str(ts_path))

    def run():
        with torch.no_grad():
            model(input_ids, attention_mask)

    return timeit(run, n_runs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pytorch-model", type=Path, required=True)
    parser.add_argument("--onnx-model", type=Path)
    parser.add_argument("--torchscript-model", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--n-runs", type=int, default=50)
    parser.add_argument("--out", type=Path, default=Path("export/artifacts/benchmark_results.json"))
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    seq_len = 64 if args.smoke_test else cfg["model"]["max_seq_length"]

    if args.smoke_test:
        model = CodeSentinelModel.from_random_config(
            num_cwe_classes=cfg["model"]["num_cwe_classes"],
            num_severity_levels=len(cfg["model"]["severity_levels"]),
        )
    else:
        model = CodeSentinelModel(
            base_model=cfg["model"]["base_model"],
            num_cwe_classes=cfg["model"]["num_cwe_classes"],
            num_severity_levels=len(cfg["model"]["severity_levels"]),
        )
        model.load_state_dict(torch.load(args.pytorch_model, map_location="cpu"))

    vocab_size = getattr(model.config, "vocab_size", 1000)
    # avoid ids 0-4: reserved special tokens (pad/bos/eos/unk/mask) a real tokenizer never emits as content
    input_ids = torch.randint(5, vocab_size, (1, seq_len), dtype=torch.long)
    attention_mask = torch.ones((1, seq_len), dtype=torch.long)

    results = {"device": "cuda" if torch.cuda.is_available() else "cpu"}
    results["pytorch"] = benchmark_pytorch(model, input_ids, attention_mask, args.n_runs)

    if args.onnx_model and args.onnx_model.exists():
        results["onnx"] = benchmark_onnx(args.onnx_model, input_ids, attention_mask, args.n_runs)
    if args.torchscript_model and args.torchscript_model.exists():
        results["torchscript"] = benchmark_torchscript(args.torchscript_model, input_ids, attention_mask, args.n_runs)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)

    for fmt, metrics in results.items():
        if isinstance(metrics, dict) and "mean_latency_ms" in metrics:
            print(f"{fmt}: {metrics['mean_latency_ms']:.2f} ms/req, {metrics['throughput_per_sec']:.1f} req/s")

    print(f"Full results written to {args.out}")


if __name__ == "__main__":
    main()
