from __future__ import annotations
import json
import time
from pathlib import Path
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.api.routes import router
from app.config import settings
from app.db.session import SessionLocal, get_db
from app.github.client import GitHubClient
from app.github.webhook import verify_signature
from app.metrics import HTTP_REQUESTS, HTTP_REQUEST_DURATION, metrics_app
from app.services.scanner import scan_diff, worst_severity

app = FastAPI(title="CodeSentinel API", version="0.1.0", description="AI-powered CI/CD vulnerability gatekeeper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.mount("/metrics", metrics_app)

@app.middleware("http")
async def observe_http_requests(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        route_name = getattr(route, "path", "unmatched")
        HTTP_REQUESTS.labels(request.method, route_name, str(status_code)).inc()
        HTTP_REQUEST_DURATION.labels(request.method, route_name).observe(time.perf_counter() - start)

@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")

def process_pull_request(payload: dict) -> None:
    installation = payload["installation"]["id"]; pull = payload["pull_request"]; repo_data = payload["repository"]
    repo_name = repo_data["full_name"]; client = GitHubClient(installation); db = SessionLocal()
    try:
        diff = client.get_pr_diff(repo_name, pull["number"])
        scan = scan_diff(db, repo_name=repo_name, pr_number=pull["number"], diff=diff, commit_sha=pull["head"]["sha"], github_repo_id=repo_data.get("id"))
        severity = worst_severity(scan); count = len(scan.findings)
        model_version = _active_model_version()
        is_demo_model = "demo" in model_version.lower() or model_version in {"unknown", "unversioned"}
        gate_enabled = settings.github_checks_enabled and not is_demo_model
        conclusion = (
            "failure" if gate_enabled and severity in {"high", "critical"}
            else "success" if gate_enabled and severity is None
            else "neutral"
        )
        summary = f"{count} finding(s); worst severity: {severity or 'none'}."
        if not gate_enabled:
            summary += " Informational only; merge blocking is disabled."
        client.post_check(repo_name, pull["head"]["sha"], conclusion, summary)
        client.post_comment(repo_name, pull["number"], f"## CodeSentinel\n{summary}")
    finally: db.close()

def _active_model_version() -> str:
    try:
        import codesentinel_model
        version_file = Path(codesentinel_model.__file__).resolve().parent / "artifacts" / "model_version.json"
        return str(json.loads(version_file.read_text(encoding="utf-8"))["model_version"])
    except (ImportError, OSError, KeyError, ValueError, TypeError):
        return "unknown"

@app.post("/webhooks/github", status_code=202)
async def github_webhook(request: Request, tasks: BackgroundTasks) -> dict[str, str]:
    raw = await request.body(); verify_signature(raw, request.headers.get("X-Hub-Signature-256"))
    payload = await request.json()
    if request.headers.get("X-GitHub-Event") != "pull_request" or payload.get("action") not in {"opened", "synchronize", "reopened"}: return {"status": "ignored"}
    if not payload.get("installation"): raise HTTPException(422, "GitHub App installation is required")
    tasks.add_task(process_pull_request, payload)
    return {"status": "accepted"}

@app.get("/health")
def health() -> dict[str, str]: return {"status": "ok"}
