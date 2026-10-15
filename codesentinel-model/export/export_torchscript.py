"""
Exports the trained CodeSentinelModel to TorchScript (traced) as the
alternative deployment format to ONNX — useful when the serving stack is
already PyTorch-native (e.g. TorchServe, mentioned in the project spec).

Usage:
    python export/export_torchscript.py --checkpoint training/final_model/model.pt \
        --config training/config.yaml --out export/artifacts/model.pt
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
from model import CodeSentinelModel  # noqa: E402


class _TorchScriptWrapper(torch.nn.Module):
    """Flattens ModelOutput into a tuple, same reasoning as the ONNX wrapper —
    torch.jit.trace can't follow a dataclass return type cleanly."""

    def __init__(self, base_model):
        super().__init__()
        self.base_model = base_model

    def forward(self, input_ids, attention_mask):
        out = self.base_model(input_ids, attention_mask)
        return out.vuln_logits, out.severity_logits, out.cwe_logits


def export_torchscript(model: torch.nn.Module, out_path: Path, seq_length: int = 512) -> None:
    model.eval()
    wrapped = _TorchScriptWrapper(model)
    vocab_size = getattr(model.config, "vocab_size", 1000)
    dummy_input_ids = torch.randint(5, vocab_size, (1, seq_length), dtype=torch.long)  # avoid ids 0-4: reserved special tokens (pad/bos/eos/unk/mask) a real tokenizer never emits as content
    dummy_attention_mask = torch.ones((1, seq_length), dtype=torch.long)

    traced = torch.jit.trace(wrapped, (dummy_input_ids, dummy_attention_mask))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    traced.save(str(out_path))
    model.eval()  # torch.jit.trace can leave the model in train() mode
                  # afterward — see the matching note in export_onnx.py.
    print(f"TorchScript model exported to {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("export/artifacts/model_ts.pt"))
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
    export_torchscript(model, args.out, seq_length=seq_len)


if __name__ == "__main__":
    main()
