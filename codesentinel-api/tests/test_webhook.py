import hashlib, hmac
from app.config import settings

def signature(payload: bytes) -> str:
    return "sha256=" + hmac.new(settings.webhook_secret.encode(), payload, hashlib.sha256).hexdigest()

def test_webhook_accepts_valid_signature(client):
    payload = b'{"action":"closed"}'
    response = client.post("/webhooks/github", content=payload, headers={"X-Hub-Signature-256": signature(payload), "X-GitHub-Event": "pull_request"})
    assert response.status_code == 202 and response.json()["status"] == "ignored"

def test_webhook_rejects_tampered_payload(client):
    payload = b'{"action":"closed"}'
    response = client.post("/webhooks/github", content=payload + b"!", headers={"X-Hub-Signature-256": signature(payload), "X-GitHub-Event": "pull_request"})
    assert response.status_code == 401
