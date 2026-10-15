from datetime import datetime
from pydantic import BaseModel, Field

class ScoreFileRequest(BaseModel):
    code_snippet: str = Field(min_length=1)
    language: str = "auto"
class ScoreFileResponse(BaseModel):
    request_id: str; timestamp: datetime; result: dict
class AnalyzePRRequest(BaseModel):
    repo: str = Field(pattern=r"^[^/]+/[^/]+$")
    pr_number: int = Field(gt=0)
    diff: str | None = None
    commit_sha: str | None = None
    github_repo_id: int | None = None
    installation_id: int | None = None
class FindingResponse(BaseModel):
    file_path: str; line_number: int; cwe_id: str | None; severity: str; confidence: float; snippet: str; model_version: str
class AnalyzePRResponse(BaseModel):
    scan_id: str; status: str; severity: str | None; findings: list[FindingResponse]
class HistoryItem(BaseModel):
    scan_id: str; repo: str; pr_number: int; status: str; started_at: datetime; completed_at: datetime | None; severity: str | None
class HistoryResponse(BaseModel):
    items: list[HistoryItem]; page: int; page_size: int; total: int
