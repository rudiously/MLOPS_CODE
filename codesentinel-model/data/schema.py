"""
Unified schema that Devign, Big-Vul, and CodeXGLUE Defect-Detection all get
normalized into before training. Keeping one schema means the rest of the
pipeline (dedup, split, augment, train) never has to know which dataset a
sample came from.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional
import hashlib
import json


SEVERITY_LEVELS = ["low", "medium", "high", "critical"]


@dataclass
class CodeSample:
    id: str
    source_dataset: str          # "devign" | "big-vul" | "codexglue"
    language: str                # "c", "cpp", "python", ...
    repo: str                    # owning repository, used for repo-level splitting
    code: str                    # the function / snippet text
    label: int                   # 0 = clean, 1 = vulnerable
    severity: Optional[str] = None          # one of SEVERITY_LEVELS, if known
    cwe_id: Optional[str] = None            # e.g. "CWE-119"; None if unlabeled
    vulnerable_lines: list[int] = field(default_factory=list)  # 1-indexed, ground truth
    commit_sha: Optional[str] = None
    function_name: Optional[str] = None

    def content_hash(self) -> str:
        """Hash of the normalized code body, used for near-duplicate detection."""
        normalized = "".join(self.code.split())  # collapse all whitespace
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(line: str) -> "CodeSample":
        return CodeSample(**json.loads(line))


def validate_sample(sample: CodeSample) -> list[str]:
    """Returns a list of validation error strings; empty list = valid."""
    errors = []
    if not sample.code or not sample.code.strip():
        errors.append("empty code body")
    if sample.label not in (0, 1):
        errors.append(f"label must be 0 or 1, got {sample.label}")
    if sample.severity is not None and sample.severity not in SEVERITY_LEVELS:
        errors.append(f"invalid severity: {sample.severity}")
    if not sample.repo:
        errors.append("missing repo (required for repo-level split)")
    if sample.label == 1 and sample.severity is None:
        # not fatal, just tracked — many vuln samples won't have severity in raw data
        pass
    return errors
