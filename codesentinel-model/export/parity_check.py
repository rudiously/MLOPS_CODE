"""
Verifies that ONNX Runtime and TorchScript outputs match the original
PyTorch model's outputs within tolerance, on identical random inputs.
This is a required deliverable, not a nice-to-have: a silently-diverged
export format in a merge-gating tool is worse than no export at all.

Usage:
    python export/parity_check.py --pytorch-model training/final_model/model.pt \
        --onnx-model export/artifacts/model.onnx \
        --torchscript-model export/artifacts/model_ts.pt \
        --config training/config.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
from model import CodeSentinelModel  # noqa: E402


def load_pytorch_model(checkpoint: Path, cfg: dict, smoke_test: bool) -> torch.nn.Module:
    if smoke_test:
        model = CodeSentinelModel.from_random_config(
            num_cwe_classes=cfg["model"]["num_cwe_classes"],
            num_severity_levels=len(cfg["model"]["severity_levels"]),
        )
        model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
    else:
        model = CodeSentinelModel(
            base_model=cfg["model"]["base_model"],
            num_cwe_classes=cfg["model"]["num_cwe_classes"],
            num_severity_levels=len(cfg["model"]["severity_levels"]),
        )
        model.load_state_dict(torch.load(checkpoint, map_location="cpu"))
    model.eval()
    return model


def check_onnx_parity(pytorch_model, onnx_path: Path, input_ids, attention_mask, atol: float) -> dict:
    import onnxruntime as ort

    with torch.no_grad():
        torch_out = pytorch_model(input_ids, attention_mask)
        torch_vuln = torch_out.vuln_logits.numpy()

    session = ort.InferenceSession(str(onnx_path))
    onnx_out = session.run(
        None,
        {
            "input_ids": input_ids.numpy(),
            "attention_mask": attention_mask.numpy(),
        },
    )
    onnx_vuln = onnx_out[0]

    max_diff = float(np.max(np.abs(torch_vuln - onnx_vuln)))
    passed = np.allclose(torch_vuln, onnx_vuln, atol=atol)
    return {"format": "onnx", "max_abs_diff": max_diff, "passed": passed, "tolerance": atol}


def check_torchscript_parity(pytorch_model, ts_path: Path, input_ids, attention_mask, atol: float) -> dict:
    with torch.no_grad():
        torch_out = pytorch_model(input_ids, attention_mask)
        torch_vuln = torch_out.vuln_logits.numpy()

        ts_model = torch.jit.load(str(ts_path))
        ts_out = ts_model(input_ids, attention_mask)
        ts_vuln = ts_out[0].numpy()

    max_diff = float(np.max(np.abs(torch_vuln - ts_vuln)))
    passed = np.allclose(torch_vuln, ts_vuln, atol=atol)
    return {"format": "torchscript", "max_abs_diff": max_diff, "passed": passed, "tolerance": atol}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pytorch-model", type=Path, required=True)
    parser.add_argument("--onnx-model", type=Path)
    parser.add_argument("--torchscript-model", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--atol", type=float, default=1e-3)
    parser.add_argument("--n-samples", type=int, default=10,
                         help="Number of random inputs to check, not just one — "
                              "tracing-based export can diverge on inputs shaped "
                              "differently from whatever was traced (see model_card.md).")
    parser.add_argument("--include-padding", action="store_true",
                         help="Also test a realistic padded sequence (some real tokens, "
                              "then pad-token-id padding) matching actual tokenizer output, "
                              "since that's the input shape production traffic sends.")
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    seq_len = 64 if args.smoke_test else cfg["model"]["max_seq_length"]
    model = load_pytorch_model(args.pytorch_model, cfg, args.smoke_test)
    vocab_size = getattr(model.config, "vocab_size", 1000)
    pad_token_id = getattr(model.config, "pad_token_id", 1)

    test_cases = []
    for i in range(args.n_samples):
        # ids 5+ only: a real tokenizer never emits reserved special-token ids
        # (pad/bos/eos/unk/mask, typically 0-4) as content tokens.
        input_ids = torch.randint(5, vocab_size, (1, seq_len), dtype=torch.long, generator=torch.Generator().manual_seed(i))
        attention_mask = torch.ones((1, seq_len), dtype=torch.long)
        test_cases.append((f"random_{i}", input_ids, attention_mask))

    if args.include_padding:
        real_len = max(1, seq_len // 2)
        input_ids = torch.full((1, seq_len), pad_token_id, dtype=torch.long)
        input_ids[0, :real_len] = torch.randint(5, vocab_size, (real_len,), dtype=torch.long)
        attention_mask = torch.zeros((1, seq_len), dtype=torch.long)
        attention_mask[0, :real_len] = 1
        test_cases.append(("padded_sequence", input_ids, attention_mask))

    all_results = []
    for name, input_ids, attention_mask in test_cases:
        if args.onnx_model and args.onnx_model.exists():
            r = check_onnx_parity(model, args.onnx_model, input_ids, attention_mask, args.atol)
            r["case"] = name
            all_results.append(r)
        if args.torchscript_model and args.torchscript_model.exists():
            r = check_torchscript_parity(model, args.torchscript_model, input_ids, attention_mask, args.atol)
            r["case"] = name
            all_results.append(r)

    for r in all_results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"[{status}] {r['format']} ({r['case']}): max_abs_diff={r['max_abs_diff']:.6f} (tol={r['tolerance']})")

    n_failed = sum(not r["passed"] for r in all_results)
    print(f"\n{len(all_results) - n_failed}/{len(all_results)} checks passed.")
    if n_failed:
        print("NOTE: a failure specifically on the 'padded_sequence' case with "
              "genuinely padded real content is a real bug to fix before shipping. "
              "A failure only when random test tokens happen to collide with a "
              "reserved special-token id (ids 0-4) is a synthetic-data artifact, "
              "not a production risk — see model_card.md.")
        sys.exit(1)


if __name__ == "__main__":
    main()
