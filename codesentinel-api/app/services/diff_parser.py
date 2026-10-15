from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass
class ChangedUnit:
    path: str
    start_line: int
    code: str

_FUNCTION = re.compile(r"^\s*(?:def |async def |function |func |(?:public|private|protected|static)\s+.*\()")

def extract_changed_units(diff: str) -> list[ChangedUnit]:
    """Extract added-line blocks from a unified diff; blocks are safe model inputs, not source parsing."""
    units: list[ChangedUnit] = []
    path = "unknown"; line_no = 0; active: list[str] = []; start = 0
    def flush() -> None:
        nonlocal active
        if active: units.append(ChangedUnit(path, start, "\n".join(active))); active = []
    for raw in diff.splitlines():
        if raw.startswith("+++ b/"):
            flush(); path = raw[6:]; continue
        hunk = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", raw)
        if hunk:
            flush(); line_no = int(hunk.group(1)); continue
        if raw.startswith("+") and not raw.startswith("+++"):
            text = raw[1:]
            if not active: start = line_no
            elif _FUNCTION.match(text): flush(); start = line_no
            active.append(text); line_no += 1
        elif raw.startswith("-"):
            continue
        else:
            flush(); line_no += 1
    flush()
    return units

def language_for_path(path: str) -> str:
    return {".py": "python", ".js": "javascript", ".ts": "typescript", ".java": "java", ".go": "go", ".rb": "ruby", ".php": "php", ".c": "c", ".cpp": "cpp"}.get("." + path.rsplit(".", 1)[-1].lower() if "." in path else "", "auto")
