from app.services import scanner

MODEL_RESULT = {"is_vulnerable": True, "confidence": 0.93, "severity": "high", "predicted_cwe": [{"cwe_id": "CWE-89", "score": 0.9}], "line_attributions": [{"line": 1, "score": 0.8, "snippet": "query = input"}], "model_version": "test-1"}
DIFF = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -0,0 +1,2 @@
+def unsafe():
+    query = input()
"""

def test_score_file_happy_path(client, monkeypatch):
    monkeypatch.setattr(scanner, "model_predict", lambda code, language: MODEL_RESULT)
    response = client.post("/score-file", json={"code_snippet": "x=1", "language": "python"})
    assert response.status_code == 200
    assert response.json()["result"]["severity"] == "high"
    assert response.json()["request_id"]

def test_score_file_validation(client):
    assert client.post("/score-file", json={"language": "python"}).status_code == 422

def test_score_file_uses_demo_artifacts_when_available(client):
    """Cross-repository smoke test: no model_predict mock."""
    import importlib.util
    from pathlib import Path
    model_root = Path(__file__).parents[2] / "codesentinel-model"
    if not (model_root / "codesentinel_model" / "artifacts" / "model.onnx").exists():
        import pytest
        pytest.skip("demo artifacts are missing")
    if importlib.util.find_spec("codesentinel_model") is None:
        import pytest
        pytest.skip("codesentinel-model is not installed")
    response = client.post("/score-file", json={"code_snippet": "int main(){char b[8]; gets(b);}", "language": "c"})
    assert response.status_code == 200
    assert response.json()["result"]["model_version"] == "demo-synthetic-0.1"

def test_root_redirects_to_docs(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code in {302, 307} and response.headers["location"] == "/docs"

def test_analyze_pr_persists_and_history(client, db_session, monkeypatch):
    monkeypatch.setattr(scanner, "model_predict", lambda code, language: MODEL_RESULT)
    response = client.post("/analyze-pr", json={"repo": "acme/demo", "pr_number": 7, "diff": DIFF, "commit_sha": "abc"})
    assert response.status_code == 200
    body = response.json(); assert body["severity"] == "high"; assert len(body["findings"]) == 1
    history = client.get("/history", params={"repo": "acme/demo", "severity": "high"})
    assert history.status_code == 200 and history.json()["total"] == 1

def test_analyze_pr_requires_installation_without_diff(client):
    assert client.post("/analyze-pr", json={"repo": "acme/demo", "pr_number": 1}).status_code == 422
