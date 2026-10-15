"""
Exports the trained CodeSentinelModel to ONNX for fast CPU/GPU inference.

Usage:
    python export/export_onnx.py --checkpoint training/final_model/model.pt \
        --config training/config.yaml --out export/artifacts/model.onnx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
from model import CodeSentinelModel  # noqa: E402


def export_onnx(model: torch.nn.Module, out_path: Path, seq_length: int = 512, opset: int = 17) -> None:
    model.eval()
    out_path = Path(out_path)
    vocab_size = getattr(model.config, "vocab_size", 1000)
    dummy_input_ids = torch.randint(5, vocab_size, (1, seq_length), dtype=torch.long)  # avoid ids 0-4: reserved special tokens (pad/bos/eos/unk/mask) a real tokenizer never emits as content
    dummy_attention_mask = torch.ones((1, seq_length), dtype=torch.long)

    class _ONNXWrapper(torch.nn.Module):
        """ONNX export needs a flat tensor tuple output, not the ModelOutput dataclass."""

        def __init__(self, base_model):
            super().__init__()
            self.base_model = base_model

        def forward(self, input_ids, attention_mask):
            out = self.base_model(input_ids, attention_mask)
            return out.vuln_logits, out.severity_logits, out.cwe_logits

    wrapped = _ONNXWrapper(model)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        wrapped,
        (dummy_input_ids, dummy_attention_mask),
        str(out_path),
        input_names=["input_ids", "attention_mask"],
        output_names=["vuln_logits", "severity_logits", "cwe_logits"],
        dynamic_axes={
            "input_ids": {0: "batch", 1: "sequence"},
            "attention_mask": {0: "batch", 1: "sequence"},
            "vuln_logits": {0: "batch"},
            "severity_logits": {0: "batch"},
            "cwe_logits": {0: "batch"},
        },
        opset_version=opset,
        dynamo=False,  # use the stable TorchScript-based exporter; the newer
                       # dynamo exporter requires the optional `onnxscript`
                       # package and is still maturing for encoder models.
    )
    # torch.onnx.export (legacy TorchScript-based path) has a known side
    # effect: it can leave the model in train() mode afterward even though
    # we called model.eval() before tracing. If the caller runs inference
    # on this same model object right after exporting, dropout being back
    # on would silently make outputs non-deterministic and wrong. Always
    # re-assert eval mode post-export.
    model.eval()
    print(f"ONNX model exported to {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("export/artifacts/model.onnx"))
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    if args.smoke_test:
        model = CodeSentinelModel.from_random_config(
            num_cwe_classes=cfg["model"]["num_cwe_classes"],
            num_severity_levels=len(cfg["model"]["severity_levels"]),
        )
        model.load_state_dict(torch.load(args.checkpoint, map_location="cpu", weights_only=True))
    else:
        model = CodeSentinelModel(
            base_model=cfg["model"]["base_model"],
            num_cwe_classes=cfg["model"]["num_cwe_classes"],
            num_severity_levels=len(cfg["model"]["severity_levels"]),
        )
        model.load_state_dict(torch.load(args.checkpoint, map_location="cpu"))

    seq_len = 64 if args.smoke_test else cfg["model"]["max_seq_length"]
    export_onnx(model, args.out, seq_length=seq_len)


if __name__ == "__main__":
    main()
