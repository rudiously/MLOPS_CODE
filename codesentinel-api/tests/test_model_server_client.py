from app.config import settings
from app.services import scanner


def test_model_predict_calls_separate_model_service(monkeypatch):
    expected = {
        "is_vulnerable": True,
        "confidence": 0.93,
        "severity": "high",
        "predicted_cwe": [],
        "line_attributions": [],
        "model_version": "test-model",
    }
    calls = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return expected

    def fake_post(url, *, json, timeout):
        calls.append((url, json, timeout))
        return Response()

    monkeypatch.setattr(settings, "model_server_url", "http://model-server:8001/")
    monkeypatch.setattr(scanner.httpx, "post", fake_post)

    assert scanner.model_predict("int main() {}", "c") == expected
    assert calls == [
        (
            "http://model-server:8001/predict",
            {"code_snippet": "int main() {}", "language": "c"},
            settings.model_server_timeout_seconds,
        )
    ]
