from datetime import datetime, timezone
import jwt
from app.config import settings
from app.db.models import PRScan, Repo, RepoAccess, User

def add_scan(db, owner: str, name: str, pr_number: int) -> Repo:
    repo = Repo(owner=owner, name=name)
    db.add(repo); db.flush()
    db.add(PRScan(repo_id=repo.id, pr_number=pr_number, status="completed", started_at=datetime.now(timezone.utc)))
    db.commit()
    return repo

def auth_header(subject: int) -> dict[str, str]:
    token = jwt.encode({"sub": str(subject)}, settings.jwt_secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}

def test_history_rejects_no_token_when_auth_required(client, monkeypatch):
    monkeypatch.setattr(settings, "require_dashboard_auth", True)
    assert client.get("/history").status_code == 401

def test_history_rejects_authenticated_user_without_row(client, monkeypatch):
    monkeypatch.setattr(settings, "require_dashboard_auth", True)
    assert client.get("/history", headers=auth_header(100)).status_code == 403

def test_history_scopes_non_admin_to_repo_access(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "require_dashboard_auth", True)
    db = db_session(); allowed = add_scan(db, "acme", "allowed", 1); add_scan(db, "acme", "private", 2)
    user = User(github_user_id=101, role="viewer"); db.add(user); db.flush(); db.add(RepoAccess(user_id=user.id, repo_id=allowed.id)); db.commit(); db.close()
    response = client.get("/history", headers=auth_header(101))
    assert response.status_code == 200
    assert [item["repo"] for item in response.json()["items"]] == ["acme/allowed"]

def test_history_admin_sees_all_repos(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "require_dashboard_auth", True)
    db = db_session(); add_scan(db, "acme", "one", 1); add_scan(db, "acme", "two", 2); db.add(User(github_user_id=102, role="admin")); db.commit(); db.close()
    response = client.get("/history", headers=auth_header(102))
    assert response.status_code == 200 and response.json()["total"] == 2
