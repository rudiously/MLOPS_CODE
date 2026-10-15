from datetime import datetime, timezone
from unittest.mock import Mock
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from app.config import settings
from app.github.client import GitHubClient

class Response:
    def __init__(self, payload=None, text=""):
        self.payload = payload or {}; self.text = text
    def raise_for_status(self): pass
    def json(self): return self.payload

def test_client_mints_jwt_exchanges_token_and_calls_github(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_key = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    public_key = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    monkeypatch.setattr(settings, "github_app_id", "12345")
    monkeypatch.setattr(settings, "github_private_key", private_key)
    monkeypatch.setattr(settings, "github_api_url", "https://github.test")
    client = GitHubClient(77)
    token = client._app_jwt()
    claims = jwt.decode(token, public_key, algorithms=["RS256"])
    assert claims["iss"] == "12345" and claims["exp"] > datetime.now(timezone.utc).timestamp()

    post = Mock(side_effect=[Response({"token": "installation-token"}), Response({"token": "installation-token"}), Response(), Response({"token": "installation-token"}), Response()])
    get = Mock(return_value=Response(text="diff --git a/a.py b/a.py"))
    monkeypatch.setattr("app.github.client.httpx.post", post)
    monkeypatch.setattr("app.github.client.httpx.get", get)
    assert client.get_pr_diff("acme/demo", 4) == "diff --git a/a.py b/a.py"
    client.post_check("acme/demo", "deadbeef", "failure", "One high finding")
    client.post_comment("acme/demo", 4, "details")

    assert post.call_args_list[0].args[0] == "https://github.test/app/installations/77/access_tokens"
    assert get.call_args.args[0] == "https://github.test/repos/acme/demo/pulls/4"
    check_call = post.call_args_list[2]
    assert check_call.args[0] == "https://github.test/repos/acme/demo/check-runs"
    assert check_call.kwargs["json"]["conclusion"] == "failure"
    comment_call = post.call_args_list[4]
    assert comment_call.args[0] == "https://github.test/repos/acme/demo/issues/4/comments"
