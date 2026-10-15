"""
Localization accuracy: a differentiator most student projects won't have.

For Big-Vul samples that carry ground-truth vulnerable_lines, checks whether
the model's top-k attributed lines overlap with the actual vulnerable
line(s). This tests not just "does the model flag vulnerable functions" but
"does it point at the right line inside them" — the thing that actually
makes the tool useful as a PR-review aid rather than a pass/fail gate.
"""
from __future__ import annotations

from dataclasses import dataclass

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from schema import CodeSample  # noqa: E402

from attributions import LineAttribution, top_k_lines  # noqa: E402


@dataclass
class LocalizationResult:
    sample_id: str
    hit: bool
    top_k_predicted_lines: list[int]
    ground_truth_lines: list[int]


def evaluate_localization(
    samples_with_attributions: list[tuple[CodeSample, list[LineAttribution]]],
    k: int = 3,
) -> dict:
    """samples_with_attributions: list of (sample, line_attributions) pairs,
    restricted to samples where sample.vulnerable_lines is non-empty and
    sample.label == 1 (only meaningful for true positives with ground truth).

    Returns overall localization accuracy (fraction of samples where at
    least one of the top-k attributed lines matches a ground-truth
    vulnerable line) plus per-sample results for the eval report.
    """
    results: list[LocalizationResult] = []
    for sample, line_attrs in samples_with_attributions:
        if not sample.vulnerable_lines:
            continue
        top_lines = [la.line_number for la in top_k_lines(line_attrs, k=k)]
        hit = any(line in sample.vulnerable_lines for line in top_lines)
        results.append(LocalizationResult(
            sample_id=sample.id,
            hit=hit,
            top_k_predicted_lines=top_lines,
            ground_truth_lines=sample.vulnerable_lines,
        ))

    if not results:
        return {"localization_accuracy": None, "n_evaluated": 0, "results": []}

    accuracy = sum(r.hit for r in results) / len(results)
    return {
        "localization_accuracy": accuracy,
        "n_evaluated": len(results),
        "k": k,
        "results": [
            {
                "sample_id": r.sample_id,
                "hit": r.hit,
                "top_k_predicted_lines": r.top_k_predicted_lines,
                "ground_truth_lines": r.ground_truth_lines,
            }
            for r in results
        ],
    }
