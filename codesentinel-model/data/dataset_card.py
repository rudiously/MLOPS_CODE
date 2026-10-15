"""
Generates data/DATASET_CARD.md summarizing the processed dataset: class
balance, language distribution, source provenance, and known limitations.

Usage:
    python data/dataset_card.py --processed-dir data/processed --out data/DATASET_CARD.md
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from schema import CodeSample


def load(path: Path) -> list[CodeSample]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [CodeSample.from_json(line) for line in f if line.strip()]


def summarize(samples: list[CodeSample]) -> dict:
    labels = Counter(s.label for s in samples)
    langs = Counter(s.language for s in samples)
    sources = Counter(s.source_dataset for s in samples)
    cwes = Counter(s.cwe_id for s in samples if s.cwe_id)
    severities = Counter(s.severity for s in samples if s.severity)
    with_line_info = sum(1 for s in samples if s.vulnerable_lines)
    return {
        "total": len(samples),
        "labels": dict(labels),
        "languages": dict(langs),
        "sources": dict(sources),
        "top_cwes": cwes.most_common(10),
        "severities": dict(severities),
        "with_line_info": with_line_info,
    }


def render_markdown(train_s, val_s, test_s) -> str:
    lines = ["# CodeSentinel Dataset Card", ""]
    for name, samples in [("Train", train_s), ("Val", val_s), ("Test", test_s)]:
        summary = summarize(samples)
        lines.append(f"## {name} split")
        lines.append(f"- Total samples: **{summary['total']}**")
        lines.append(f"- Label balance (0=clean, 1=vulnerable): `{summary['labels']}`")
        lines.append(f"- Source datasets: `{summary['sources']}`")
        lines.append(f"- Languages: `{summary['languages']}`")
        lines.append(f"- Samples with line-level ground truth: **{summary['with_line_info']}**")
        if summary["severities"]:
            lines.append(f"- Severity distribution: `{summary['severities']}`")
        if summary["top_cwes"]:
            lines.append(f"- Top CWE categories: `{summary['top_cwes']}`")
        lines.append("")

    lines += [
        "## Known limitations",
        "- Devign/CodeXGLUE labels are function-level, not line-level — the model's "
        "line-attribution output for those samples is unsupervised (explainability "
        "only), not validated against ground truth.",
        "- C/C++ dominates all three source datasets; performance on other languages "
        "(Python, Java, JS) is not covered by this training data and should be "
        "treated as out-of-distribution until a language-specific eval is added.",
        "- Repo-level splitting avoids leakage but means some repos with heavy "
        "vulnerability activity may be entirely absent from train or test — check "
        "split_manifest.json if a particular repo's coverage matters to you.",
        "- Dedup is content-hash based on normalized whitespace; renamed-but-identical "
        "functions across forks may still collide or slip through.",
        "",
        "## License note",
        "Devign, Big-Vul, and CodeXGLUE are each released under their own upstream "
        "licenses/terms (research use). Verify current terms before any commercial "
        "use of a model trained on this combined set.",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--out", type=Path, default=Path("data/DATASET_CARD.md"))
    args = parser.parse_args()

    train_s = load(args.processed_dir / "train.jsonl")
    val_s = load(args.processed_dir / "val.jsonl")
    test_s = load(args.processed_dir / "test.jsonl")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_markdown(train_s, val_s, test_s), encoding="utf-8")
    print(f"Dataset card written to {args.out}")


if __name__ == "__main__":
    main()
