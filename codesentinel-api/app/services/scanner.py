from __future__ import annotations
from datetime import datetime, timezone
import time
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import settings
from app.db.models import Finding, PRScan, Repo
from app.services.diff_parser import extract_changed_units, language_for_path
from app.metrics import MODEL_INFERENCES, MODEL_INFERENCE_DURATION, SCANS

SEVERITY = {"low": 1, "medium": 2, "high": 3, "critical": 4}

def model_predict(code: str, language: str) -> dict:
    started = time.perf_counter()
    try:
        if settings.model_server_url:
            response = httpx.post(
                f"{settings.model_server_url.rstrip('/')}/predict",
                json={"code_snippet": code, "language": language},
                timeout=settings.model_server_timeout_seconds,
            )
            response.raise_for_status()
            result = response.json()
        else:
            from codesentinel_model import predict
            result = predict(code, language)
        MODEL_INFERENCES.labels("success").inc()
        return result
    except Exception:
        MODEL_INFERENCES.labels("error").inc()
        raise
    finally:
        MODEL_INFERENCE_DURATION.observe(time.perf_counter() - started)

def find_or_create_repo(db: Session, full_name: str, github_repo_id: int | None = None) -> Repo:
    owner, name = full_name.split("/", 1)
    repo = db.scalar(select(Repo).where(Repo.github_repo_id == github_repo_id)) if github_repo_id else db.scalar(select(Repo).where(Repo.owner == owner, Repo.name == name))
    if repo is None:
        repo = Repo(owner=owner, name=name, github_repo_id=github_repo_id); db.add(repo); db.flush()
    return repo

def scan_diff(db: Session, *, repo_name: str, pr_number: int, diff: str, commit_sha: str | None = None, github_repo_id: int | None = None) -> PRScan:
    repo = find_or_create_repo(db, repo_name, github_repo_id)
    scan = PRScan(repo_id=repo.id, pr_number=pr_number, commit_sha=commit_sha, status="running")
    db.add(scan); db.flush()
    try:
        for unit in extract_changed_units(diff):
            result = model_predict(unit.code, language_for_path(unit.path))
            if not result["is_vulnerable"]: continue
            attributions = result.get("line_attributions", []) or [{"line": 1, "snippet": unit.code}]
            cwes = result.get("predicted_cwe", [])
            cwe = cwes[0]["cwe_id"] if cwes else None
            for attribution in attributions:
                db.add(Finding(scan_id=scan.id, file_path=unit.path, line_number=unit.start_line + max(0, int(attribution.get("line", 1)) - 1), cwe_id=cwe, severity=result["severity"], confidence=float(result["confidence"]), snippet=str(attribution.get("snippet") or unit.code), model_version=str(result["model_version"])))
        scan.status = "completed"; scan.completed_at = datetime.now(timezone.utc); db.commit(); db.refresh(scan)
        SCANS.labels("completed").inc()
    except Exception:
        scan.status = "failed"; scan.completed_at = datetime.now(timezone.utc); db.commit(); SCANS.labels("failed").inc(); raise
    return scan

def worst_severity(scan: PRScan) -> str | None:
    return max((f.severity for f in scan.findings), key=lambda value: SEVERITY.get(value, 0), default=None)
