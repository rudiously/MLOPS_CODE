"""
Downloads raw source data for Devign, Big-Vul, and CodeXGLUE Defect-Detection.

Run this on a machine with normal internet access (Colab/Kaggle/your box) —
it is not run inside restricted sandboxes. Each dataset lives behind a
different distribution channel, so this script documents + automates the
actual retrieval steps rather than assuming one API covers all three.

Usage:
    python data/download.py --dataset all --out data/raw/
    python data/download.py --dataset devign --out data/raw/
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SOURCES = {
    # Devign: function-level C/C++ vulnerability labels, released via the
    # authors' repo / HF datasets mirror.
    "devign": {
        "hf_dataset": "google/code_x_glue_cc_defect_detection",  # CodeXGLUE packages Devign
        "notes": "CodeXGLUE's Defect-Detection task IS Devign, repackaged with a "
                 "standard train/val/test split. If you want the raw Devign labels "
                 "instead, clone https://github.com/epicosy/devign",
    },
    "big-vul": {
        "hf_dataset": "bstee615/bigvul",
        "notes": "Big-Vul additionally provides CWE ids and vulnerable line numbers "
                 "(the 'vul_func_with_fix' columns) — this is what makes the "
                 "localization-accuracy metric possible. Falls back to manual CSV "
                 "download from https://github.com/ZeoVan/MSR_20_Code_vulnerability_CSV_Dataset "
                 "if the HF mirror is unavailable.",
    },
    "codexglue": {
        "hf_dataset": "google/code_x_glue_cc_defect_detection",
        "notes": "Same underlying data as devign here; kept as a separate key so "
                 "the merge step can track provenance per the schema.",
    },
}


def download_hf(dataset_name: str, out_dir: Path) -> None:
    try:
        from datasets import load_dataset
    except ImportError:
        print("Install the `datasets` package first: pip install datasets", file=sys.stderr)
        raise

    spec = SOURCES[dataset_name]
    print(f"[{dataset_name}] downloading {spec['hf_dataset']} ...")
    ds = load_dataset(spec["hf_dataset"])
    dest = out_dir / dataset_name
    dest.mkdir(parents=True, exist_ok=True)
    for split_name, split in ds.items():
        split.to_json(str(dest / f"{split_name}.jsonl"))
    print(f"[{dataset_name}] saved to {dest}")
    print(f"[{dataset_name}] note: {spec['notes']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["all", *SOURCES.keys()], default="all")
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    targets = list(SOURCES.keys()) if args.dataset == "all" else [args.dataset]
    for name in targets:
        try:
            download_hf(name, args.out)
        except Exception as e:  # noqa: BLE001 - report and continue with other sources
            print(f"[{name}] FAILED: {e}", file=sys.stderr)
            print(f"[{name}] fallback instructions: {SOURCES[name]['notes']}", file=sys.stderr)


if __name__ == "__main__":
    main()
