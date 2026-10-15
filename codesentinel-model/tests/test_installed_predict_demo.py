import json
from pathlib import Path

import pytest


def test_installed_predict_uses_demo_artifacts_and_matches_schema():
    pytest.importorskip("onnxruntime")
    root = Path(__file__).parents[1]
    if not (root / "codesentinel_model" / "artifacts" / "model.onnx").exists():
        pytest.skip("demo artifacts are missing; run scripts/build_demo_artifacts.py")
    from jsonschema import validate
    from codesentinel_model import predict

    result = predict("int main(){char b[8]; gets(b);}", "c")
    validate(result, json.loads((root / "codesentinel_model" / "output_schema.json").read_text()))
    assert result["model_version"] == "demo-synthetic-0.1"
