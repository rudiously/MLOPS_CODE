import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "export"))

from model import CodeSentinelModel  # noqa: E402


@pytest.fixture
def tiny_model():
    m = CodeSentinelModel.from_random_config(
        num_cwe_classes=5, num_severity_levels=4, hidden_size=32, num_layers=1, vocab_size=200
    )
    m.eval()
    return m


def test_onnx_export_and_parity(tmp_path, tiny_model):
    onnxruntime = pytest.importorskip("onnxruntime")
    from export_onnx import export_onnx

    onnx_path = tmp_path / "model.onnx"
    export_onnx(tiny_model, onnx_path, seq_length=16)
    assert onnx_path.exists()

    # ids 5+ only: a real tokenizer never emits ids 0-4 (pad/bos/eos/unk/mask)
    # as content, so this matches genuine inference input. See model_card.md
    # "Known export caveat" for what happens if a special-token id appears
    # as real content (a synthetic-data-only scenario).
    input_ids = torch.randint(5, 200, (1, 16), dtype=torch.long)
    attention_mask = torch.ones((1, 16), dtype=torch.long)

    with torch.no_grad():
        torch_out = tiny_model(input_ids, attention_mask)

    session = onnxruntime.InferenceSession(str(onnx_path))
    onnx_out = session.run(None, {
        "input_ids": input_ids.numpy(), "attention_mask": attention_mask.numpy(),
    })

    import numpy as np
    assert np.allclose(torch_out.vuln_logits.numpy(), onnx_out[0], atol=1e-3)


def test_torchscript_export_and_parity(tmp_path, tiny_model):
    from export_torchscript import export_torchscript

    ts_path = tmp_path / "model_ts.pt"
    export_torchscript(tiny_model, ts_path, seq_length=16)
    assert ts_path.exists()

    input_ids = torch.randint(5, 200, (1, 16), dtype=torch.long)
    attention_mask = torch.ones((1, 16), dtype=torch.long)

    with torch.no_grad():
        torch_out = tiny_model(input_ids, attention_mask)
        ts_model = torch.jit.load(str(ts_path))
        ts_out = ts_model(input_ids, attention_mask)

    assert torch.allclose(torch_out.vuln_logits, ts_out[0], atol=1e-4)
