"""
Deduplicates near-identical functions across datasets and produces a
repo-level train/val/test split (never a function-level split — that would
leak near-duplicate functions from the same repo across splits and inflate
eval numbers, which is a common mistake in vulnerability-detection papers).

Usage:
    python data/dedup_split.py --in data/processed/all_samples.jsonl \
        --out-dir data/processed/ --test-frac 0.15 --val-frac 0.15 --seed 42
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from schema import CodeSample


def load_samples(path: Path) -> list[CodeSample]:
    with open(path, "r", encoding="utf-8") as f:
        return [CodeSample.from_json(line) for line in f if line.strip()]


def dedup(samples: list[CodeSample]) -> tuple[list[CodeSample], int]:
    """Exact + normalized-whitespace dedup. Keeps first occurrence, prefers
    the copy that has the richest metadata (severity/cwe/line info) when a
    duplicate is found across datasets."""
    best_by_hash: dict[str, CodeSample] = {}
    for s in samples:
        h = s.content_hash()
        if h not in best_by_hash:
            best_by_hash[h] = s
            continue
        existing = best_by_hash[h]
        existing_richness = sum([
            existing.severity is not None,
            existing.cwe_id is not None,
            len(existing.vulnerable_lines) > 0,
        ])
        new_richness = sum([
            s.severity is not None,
            s.cwe_id is not None,
            len(s.vulnerable_lines) > 0,
        ])
        if new_richness > existing_richness:
            best_by_hash[h] = s

    deduped = list(best_by_hash.values())
    removed = len(samples) - len(deduped)
    return deduped, removed


def repo_level_split(
    samples: list[CodeSample],
    test_frac: float,
    val_frac: float,
    seed: int,
) -> tuple[list[CodeSample], list[CodeSample], list[CodeSample]]:
    by_repo: dict[str, list[CodeSample]] = defaultdict(list)
    for s in samples:
        by_repo[s.repo].append(s)

    repos = list(by_repo.keys())
    if len(repos) < 3:
        raise ValueError(
            "A repo-level train/validation/test split needs at least 3 distinct repos; "
            f"found {len(repos)} ({', '.join(sorted(repos)) or 'none'}). "
            "Add data covering more repositories before claiming held-out-repo metrics."
        )
    rng = random.Random(seed)
    rng.shuffle(repos)

    n_repos = len(repos)
    n_test = max(1, int(n_repos * test_frac))
    n_val = max(1, int(n_repos * val_frac))

    test_repos = set(repos[:n_test])
    val_repos = set(repos[n_test:n_test + n_val])
    train_repos = set(repos[n_test + n_val:])

    train = [s for r in train_repos for s in by_repo[r]]
    val = [s for r in val_repos for s in by_repo[r]]
    test = [s for r in test_repos for s in by_repo[r]]
    if not train or not val or not test:
        raise ValueError(
            "Repo-level split produced an empty partition. Add more distinct repositories "
            "or adjust the split fractions before training."
        )
    return train, val, test


def write_jsonl(samples: list[CodeSample], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(s.to_json() + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--test-frac", type=float, default=0.15)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    samples = load_samples(args.in_path)
    deduped, removed = dedup(samples)
    print(f"Deduped {len(samples)} -> {len(deduped)} samples ({removed} removed)")

    train, val, test = repo_level_split(deduped, args.test_frac, args.val_frac, args.seed)
    print(f"Split by repo: train={len(train)} val={len(val)} test={len(test)}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(train, args.out_dir / "train.jsonl")
    write_jsonl(val, args.out_dir / "val.jsonl")
    write_jsonl(test, args.out_dir / "test.jsonl")

    manifest = {
        "seed": args.seed,
        "test_frac": args.test_frac,
        "val_frac": args.val_frac,
        "counts": {"train": len(train), "val": len(val), "test": len(test)},
        "train_repos": sorted({s.repo for s in train}),
        "val_repos": sorted({s.repo for s in val}),
        "test_repos": sorted({s.repo for s in test}),
        "dedup_removed": removed,
    }
    with open(args.out_dir / "split_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Split manifest written to {args.out_dir / 'split_manifest.json'}")


if __name__ == "__main__":
    main()
