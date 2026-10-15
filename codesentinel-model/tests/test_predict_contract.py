import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "training"))
sys.path.insert(0, str(REPO_ROOT / "export"))


@pytest.fixture
def onnx_model_path(tmp_path):
    onnxruntime = pytest.importorskip("onnxruntime")  # noqa: F841
    from model import CodeSentinelModel
    from export_onnx import export_onnx

    model = CodeSentinelModel.from_random_config(
        num_cwe_classes=5, num_severity_levels=4, hidden_size=32, num_layers=1, vocab_size=200
    )
    out_path = tmp_path / "model.onnx"
    export_onnx(model, out_path, seq_length=32)
    return out_path


def test_output_schema_file_is_valid_json():
    schema_path = REPO_ROOT / "codesentinel_model" / "output_schema.json"
    schema = json.loads(schema_path.read_text())
    assert schema["title"] == "CodeSentinelPredictionOutput"
    required = set(schema["required"])
    assert required == {
        "is_vulnerable", "confidence", "severity", "predicted_cwe",
        "line_attributions", "model_version",
    }


def test_predict_output_matches_schema_shape(onnx_model_path, monkeypatch):
    """Exercises CodeSentinelPredictor end-to-end against the tiny exported
    ONNX model, using a from-scratch tokenizer stand-in so this test needs
    no network access to the HF hub."""
    pytest.importorskip("onnxruntime")
    from codesentinel_model.predict import CodeSentinelPredictor, PredictorConfig

    class _FakeTokenizer:
        def __call__(self, text, truncation, max_length, padding, return_tensors):
            import numpy as np
            ids = [hash(tok) % 200 for tok in text.split()][:max_length]
            ids += [0] * (max_length - len(ids))
            attn = [1] * min(len(text.split()), max_length) + [0] * max(0, max_length - len(text.split()))
            attn = attn[:max_length]
            return {"input_ids": np.array([ids]), "attention_mask": np.array([attn])}

    predictor = CodeSentinelPredictor.__new__(CodeSentinelPredictor)
    predictor.config = PredictorConfig(model_path=onnx_model_path, max_length=32)
    import onnxruntime as ort
    predictor._session = ort.InferenceSession(str(onnx_model_path))
    predictor._tokenizer = _FakeTokenizer()
    predictor._cwe_vocab = {}
    predictor._idx_to_cwe = {}

    result = predictor.predict("int main() { char buf[10]; strcpy(buf, input); return 0; }")

    assert isinstance(result["is_vulnerable"], bool)
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["severity"] in {"low", "medium", "high", "critical"}
    assert isinstance(result["predicted_cwe"], list)
    assert isinstance(result["line_attributions"], list)
    assert isinstance(result["model_version"], str)
