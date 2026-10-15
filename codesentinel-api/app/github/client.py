from __future__ import annotations
from datetime import datetime, timedelta, timezone
import httpx, jwt
from app.config import settings

class GitHubClient:
    def __init__(self, installation_id: int): self.installation_id = installation_id
    def _app_jwt(self) -> str:
        if not settings.github_app_id or not settings.github_private_key: raise RuntimeError("GitHub App credentials are not configured")
        now = datetime.now(timezone.utc)
        return jwt.encode({"iat": now - timedelta(seconds=60), "exp": now + timedelta(minutes=9), "iss": settings.github_app_id}, settings.github_private_key.replace("\\n", "\n"), algorithm="RS256")
    def _token(self) -> str:
        response = httpx.post(f"{settings.github_api_url}/app/installations/{self.installation_id}/access_tokens", headers={"Authorization": f"Bearer {self._app_jwt()}", "Accept": "application/vnd.github+json"}, timeout=20)
        response.raise_for_status(); return response.json()["token"]
    def _headers(self) -> dict[str, str]: return {"Authorization": f"Bearer {self._token()}", "Accept": "application/vnd.github+json"}
    def get_pr_diff(self, repo: str, pr_number: int) -> str:
        response = httpx.get(f"{settings.github_api_url}/repos/{repo}/pulls/{pr_number}", headers={**self._headers(), "Accept": "application/vnd.github.v3.diff"}, timeout=30); response.raise_for_status(); return response.text
    def post_check(self, repo: str, sha: str, conclusion: str, summary: str) -> None:
        response = httpx.post(f"{settings.github_api_url}/repos/{repo}/check-runs", headers=self._headers(), json={"name": "CodeSentinel", "head_sha": sha, "status": "completed", "conclusion": conclusion, "output": {"title": "CodeSentinel scan", "summary": summary}}, timeout=30); response.raise_for_status()
    def post_comment(self, repo: str, pr_number: int, body: str) -> None:
        response = httpx.post(f"{settings.github_api_url}/repos/{repo}/issues/{pr_number}/comments", headers=self._headers(), json={"body": body}, timeout=30); response.raise_for_status()
