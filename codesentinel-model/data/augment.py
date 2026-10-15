"""
Semantics-preserving adversarial augmentations for C/C++-style code:
variable renaming, dead-code insertion, statement reordering (where safe).

These are used two ways:
  1. As optional training-time augmentation (--augment flag in train.py)
  2. As an eval-time robustness probe (evaluation/generate_report.py runs the
     test set through these transforms and reports the F1 drop)

Kept intentionally simple/regex-based rather than a full AST transform, since
the goal is a robustness *signal*, not a production code transformer.
"""
from __future__ import annotations

import random
import re

_VAR_TOKEN_RE = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b")
_RESERVED = {
    "if", "else", "for", "while", "return", "int", "char", "float", "double",
    "void", "struct", "switch", "case", "break", "continue", "sizeof", "static",
    "const", "unsigned", "signed", "long", "short", "typedef", "include",
    "define", "public", "private", "class", "new", "delete", "this", "namespace",
}


def rename_variables(code: str, rename_frac: float = 0.3, seed: int | None = None) -> str:
    rng = random.Random(seed)
    tokens = sorted(set(_VAR_TOKEN_RE.findall(code)) - _RESERVED)
    n_to_rename = max(1, int(len(tokens) * rename_frac)) if tokens else 0
    targets = rng.sample(tokens, min(n_to_rename, len(tokens))) if tokens else []
    mapping = {t: f"var_{i}" for i, t in enumerate(targets)}

    def _sub(match: re.Match) -> str:
        word = match.group(0)
        return mapping.get(word, word)

    return _VAR_TOKEN_RE.sub(_sub, code)


def insert_dead_code(code: str, seed: int | None = None) -> str:
    rng = random.Random(seed)
    dead_snippets = [
        "int __unused_tmp = 0;",
        "if (0) { continue; }",
        "/* no-op */;",
        "static int __noop_counter = 0; __noop_counter++;",
    ]
    lines = code.split("\n")
    if len(lines) < 2:
        return code
    insert_at = rng.randint(1, len(lines) - 1)
    lines.insert(insert_at, rng.choice(dead_snippets))
    return "\n".join(lines)


def reorder_independent_statements(code: str, seed: int | None = None) -> str:
    """Very conservative: only swaps adjacent lines that are both simple
    variable declarations with no shared identifiers, to avoid breaking
    semantics. If nothing qualifies, returns the code unchanged."""
    rng = random.Random(seed)
    lines = code.split("\n")
    decl_re = re.compile(r"^\s*(int|float|double|char|long|short)\s+\w+\s*=?.*;\s*$")
    for i in range(len(lines) - 1):
        if decl_re.match(lines[i]) and decl_re.match(lines[i + 1]):
            var_a = re.findall(r"\b\w+\b", lines[i])
            var_b = re.findall(r"\b\w+\b", lines[i + 1])
            if not set(var_a) & set(var_b):
                if rng.random() < 0.5:
                    lines[i], lines[i + 1] = lines[i + 1], lines[i]
    return "\n".join(lines)


def augment(code: str, seed: int | None = None) -> str:
    """Applies all three transforms in sequence — used both for training-time
    augmentation and the robustness eval probe."""
    code = rename_variables(code, seed=seed)
    code = insert_dead_code(code, seed=seed)
    code = reorder_independent_statements(code, seed=seed)
    return code
