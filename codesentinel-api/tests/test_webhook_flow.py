import hashlib, hmac, json
from types import SimpleNamespace
from app.config import settings
from app import main

class FakeGitHubClient:
    instances = []
    def __init__(self, installation_id): self.installation_id = installation_id; self.calls = []; self.__class__.instances.append(self)
    def get_pr_diff(self, repo, number): self.calls.append(("diff", repo, number)); return "unused"
    def post_check(self, repo, sha, conclusion, summary): self.calls.append(("check", repo, sha, conclusion, summary))
    def post_comment(self, repo, number, body): self.calls.append(("comment", repo, number, body))

def test_opened_webhook_runs_scan_and_posts_check_and_comment(client, db_session, monkeypatch):
    FakeGitHubClient.instances.clear()
    monkeypatch.setattr(main, "GitHubClient", FakeGitHubClient)
    monkeypatch.setattr(main, "SessionLocal", db_session)
    monkeypatch.setattr(main, "scan_diff", lambda *args, **kwargs: SimpleNamespace(findings=[SimpleNamespace(severity="high")]))
    monkeypatch.setattr(main, "worst_severity", lambda scan: "high")
    payload = {"action": "opened", "installation": {"id": 7}, "repository": {"id": 99, "full_name": "acme/demo"}, "pull_request": {"number": 3, "head": {"sha": "abc123"}}}
    raw = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(settings.webhook_secret.encode(), raw, hashlib.sha256).hexdigest()
    response = client.post("/webhooks/github", content=raw, headers={"X-Hub-Signature-256": signature, "X-GitHub-Event": "pull_request"})
    assert response.status_code == 202
    calls = FakeGitHubClient.instances[0].calls
    assert ("check", "acme/demo", "abc123", "neutral", "1 finding(s); worst severity: high. Informational only; merge blocking is disabled.") in calls
    assert ("comment", "acme/demo", 3, "## CodeSentinel\n1 finding(s); worst severity: high. Informational only; merge blocking is disabled.") in calls
