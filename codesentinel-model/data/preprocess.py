"""
Normalizes raw Devign / Big-Vul / CodeXGLUE jsonl exports into the unified
CodeSample schema (see schema.py) and writes one combined jsonl file.

Usage:
    python data/preprocess.py --raw-dir data/raw/ --out data/processed/all_samples.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from schema import CodeSample, validate_sample


def normalize_codexglue_row(row: dict, idx: int) -> CodeSample:
    # CodeXGLUE defect-detection rows: {"func": str, "target": 0/1, "project": str, "commit_id": str}
    return CodeSample(
        id=f"codexglue-{idx}",
        source_dataset="codexglue",
        language="c",
        repo=row.get("project", "unknown"),
        code=row.get("func", ""),
        label=int(row.get("target", 0)),
        commit_sha=row.get("commit_id"),
    )


def normalize_bigvul_row(row: dict, idx: int) -> CodeSample:
    # Big-Vul rows carry CWE id + line-level info when available.
    vuln_lines = []
    raw_lines = row.get("vul_lines") or row.get("lines_before") or []
    if isinstance(raw_lines, str):
        vuln_lines = [int(x) for x in raw_lines.split(",") if x.strip().isdigit()]
    elif isinstance(raw_lines, list):
        vuln_lines = [int(x) for x in raw_lines if str(x).isdigit()]

    label = int(row.get("vul", row.get("target", 0)))
    severity = None
    cvss = row.get("CVSS_Score") or row.get("cvss_score")
    if cvss is not None:
        try:
            cvss = float(cvss)
            severity = (
                "low" if cvss < 4 else
                "medium" if cvss < 7 else
                "high" if cvss < 9 else
                "critical"
            )
        except (TypeError, ValueError):
            severity = None

    return CodeSample(
        id=f"bigvul-{idx}",
        source_dataset="big-vul",
        language=row.get("lang", "c"),
        repo=row.get("project", row.get("repo", "unknown")),
        code=row.get("func_before", row.get("code", "")),
        label=label,
        severity=severity,
        cwe_id=row.get("CWE_ID") or row.get("cwe_id"),
        vulnerable_lines=vuln_lines,
        commit_sha=row.get("commit_id"),
        function_name=row.get("func_name"),
    )


def normalize_devign_row(row: dict, idx: int) -> CodeSample:
    return CodeSample(
        id=f"devign-{idx}",
        source_dataset="devign",
        language="c",
        repo=row.get("project", "unknown"),
        code=row.get("func", row.get("code", "")),
        label=int(row.get("target", row.get("label", 0))),
    )


NORMALIZERS = {
    "codexglue": normalize_codexglue_row,
    "big-vul": normalize_bigvul_row,
    "devign": normalize_devign_row,
}


def process_file(path: Path, dataset_key: str) -> list[CodeSample]:
    samples = []
    normalizer = NORMALIZERS[dataset_key]
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            sample = normalizer(row, idx=i)
            errors = validate_sample(sample)
            if errors:
                continue  # skip malformed rows rather than crash the pipeline
            samples.append(sample)
    return samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("data/processed/all_samples.jsonl"))
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with open(args.out, "w", encoding="utf-8") as out_f:
        for dataset_key in NORMALIZERS:
            dataset_dir = args.raw_dir / dataset_key
            if not dataset_dir.exists():
                print(f"skipping {dataset_key}: {dataset_dir} not found")
                continue
            for split_file in dataset_dir.glob("*.jsonl"):
                samples = process_file(split_file, dataset_key)
                for s in samples:
                    out_f.write(s.to_json() + "\n")
                total += len(samples)
                print(f"[{dataset_key}] {split_file.name}: {len(samples)} valid samples")
    print(f"Total normalized samples written to {args.out}: {total}")


if __name__ == "__main__":
    main()
