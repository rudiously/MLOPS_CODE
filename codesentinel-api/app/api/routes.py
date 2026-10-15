from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from app.auth.dependencies import require_dashboard_user
from app.config import settings
from app.db.models import Finding, PRScan, Repo, RepoAccess, User
from app.db.session import get_db
from app.github.client import GitHubClient
from app.schemas.api import AnalyzePRRequest, AnalyzePRResponse, FindingResponse, HistoryItem, HistoryResponse, ScoreFileRequest, ScoreFileResponse
from app.services import scanner
from app.services.scanner import scan_diff, worst_severity

router = APIRouter()

def response_for_scan(scan: PRScan) -> AnalyzePRResponse:
    return AnalyzePRResponse(scan_id=scan.id, status=scan.status, severity=worst_severity(scan), findings=[FindingResponse(file_path=f.file_path, line_number=f.line_number, cwe_id=f.cwe_id, severity=f.severity, confidence=f.confidence, snippet=f.snippet, model_version=f.model_version) for f in scan.findings])

@router.post("/score-file", response_model=ScoreFileResponse)
def score_file(body: ScoreFileRequest) -> ScoreFileResponse:
    return ScoreFileResponse(request_id=str(uuid4()), timestamp=datetime.now(timezone.utc), result=scanner.model_predict(body.code_snippet, body.language))

@router.post("/analyze-pr", response_model=AnalyzePRResponse)
def analyze_pr(body: AnalyzePRRequest, db: Session = Depends(get_db)) -> AnalyzePRResponse:
    diff = body.diff
    if diff is None:
        if body.installation_id is None: raise HTTPException(status_code=422, detail="installation_id is required when diff is omitted")
        diff = GitHubClient(body.installation_id).get_pr_diff(body.repo, body.pr_number)
    scan = scan_diff(db, repo_name=body.repo, pr_number=body.pr_number, diff=diff, commit_sha=body.commit_sha, github_repo_id=body.github_repo_id)
    return response_for_scan(scan)

@router.get("/history", response_model=HistoryResponse)
def history(repo: str | None = None, severity: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"), date_from: datetime | None = None, date_to: datetime | None = None, page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100), _user: dict = Depends(require_dashboard_user), db: Session = Depends(get_db)) -> HistoryResponse:
    query = select(PRScan).join(Repo).options(selectinload(PRScan.repo), selectinload(PRScan.findings))
    count_query = select(func.count(PRScan.id)).join(Repo)
    filters = []
    if settings.require_dashboard_auth:
        identity = _user.get("github_user_id", _user.get("sub"))
        try: github_user_id = int(identity)
        except (TypeError, ValueError): raise HTTPException(401, "Token must contain a numeric sub or github_user_id")
        user = db.scalar(select(User).where(User.github_user_id == github_user_id))
        if user is None: raise HTTPException(403, "User has no CodeSentinel access")
        if user.role != "admin":
            query = query.join(RepoAccess, RepoAccess.repo_id == Repo.id)
            count_query = count_query.join(RepoAccess, RepoAccess.repo_id == Repo.id)
            filters.append(RepoAccess.user_id == user.id)
    if repo:
        if "/" not in repo: raise HTTPException(422, "repo must be owner/name")
        owner, name = repo.split("/", 1); filters.extend([Repo.owner == owner, Repo.name == name])
    if severity: filters.append(PRScan.findings.any(Finding.severity == severity))
    if date_from: filters.append(PRScan.started_at >= date_from)
    if date_to: filters.append(PRScan.started_at <= date_to)
    total = db.scalar(count_query.where(*filters)) or 0
    scans = db.scalars(query.where(*filters).order_by(PRScan.started_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return HistoryResponse(items=[HistoryItem(scan_id=s.id, repo=f"{s.repo.owner}/{s.repo.name}", pr_number=s.pr_number, status=s.status, started_at=s.started_at, completed_at=s.completed_at, severity=worst_severity(s)) for s in scans], page=page, page_size=page_size, total=total)

@router.get("/scans/{scan_id}", response_model=AnalyzePRResponse)
def get_scan(scan_id: str, db: Session = Depends(get_db)) -> AnalyzePRResponse:
    scan = db.scalar(select(PRScan).where(PRScan.id == scan_id).options(selectinload(PRScan.findings)))
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return response_for_scan(scan)

