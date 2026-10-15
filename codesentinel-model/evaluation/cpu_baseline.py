"""Train a lightweight CPU baseline and evaluate it with leave-one-repo-out splits.

This is a dataset and evaluation baseline, not the production ONNX model. It is
useful when accelerator hardware is unavailable and must not be treated as a
validated security gate.

Usage:
    python evaluation/cpu_baseline.py
"""
from __future__ import annotations

import json
import joblib
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.pipeline import FeatureUnion, Pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data"))
from schema import CodeSample  # noqa: E402
from dedup_split import dedup  # noqa: E402


def load_deduplicated_samples(path: Path) -> list[CodeSample]:
    with path.open(encoding="utf-8") as handle:
        samples = [CodeSample.from_json(line) for line in handle if line.strip()]
    unique, removed = dedup(samples)
    print(f"Loaded {len(samples)} samples; removed {removed} exact/whitespace duplicates")
    return unique


def make_pipeline() -> Pipeline:
    features = FeatureUnion([
        ("words", TfidfVectorizer(
            analyzer="word", ngram_range=(1, 2), min_df=2, max_features=80_000,
            sublinear_tf=True, dtype=np.float32,
        )),
        ("characters", TfidfVectorizer(
            analyzer="char", ngram_range=(3, 5), min_df=3, max_features=160_000,
            sublinear_tf=True, dtype=np.float32,
        )),
    ])
    return Pipeline([
        ("features", features),
        ("classifier", LogisticRegression(
            C=2.0, class_weight="balanced", max_iter=300, solver="liblinear",
            random_state=42, tol=1e-3,
        )),
    ])


def main() -> None:
    samples = load_deduplicated_samples(ROOT / "data/processed/all_samples.jsonl")
    by_repo: dict[str, list[CodeSample]] = defaultdict(list)
    for sample in samples:
        by_repo[sample.repo].append(sample)
    if len(by_repo) < 2:
        raise ValueError(f"Leave-one-repo-out evaluation needs 2+ repos; found {len(by_repo)}")

    rows = []
    for held_out_repo in sorted(by_repo):
        train = [s for repo, group in by_repo.items() if repo != held_out_repo for s in group]
        test = by_repo[held_out_repo]
        y_train = np.asarray([s.label for s in train], dtype=np.int64)
        y_test = np.asarray([s.label for s in test], dtype=np.int64)
        if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
            raise ValueError(f"Both classes are required in train and held-out repo {held_out_repo}")

        model = make_pipeline()
        start = time.monotonic()
        model.fit([s.code for s in train], y_train)
        probabilities = model.predict_proba([s.code for s in test])[:, 1]
        predictions = (probabilities >= 0.5).astype(np.int64)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, predictions, average="binary", zero_division=0
        )
        matrix = confusion_matrix(y_test, predictions, labels=[0, 1])
        metrics = {
            "held_out_repo": held_out_repo,
            "train_rows": len(train),
            "test_rows": len(test),
            "train_label_counts": dict(Counter(map(int, y_train))),
            "test_label_counts": dict(Counter(map(int, y_test))),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "roc_auc": float(roc_auc_score(y_test, probabilities)),
            "confusion_matrix_labels_0_1": matrix.tolist(),
            "fit_and_predict_seconds": round(time.monotonic() - start, 2),
        }
        rows.append(metrics)
        print(
            f"held out {held_out_repo}: precision={precision:.4f} "
            f"recall={recall:.4f} f1={f1:.4f} auc={metrics['roc_auc']:.4f}"
        )

    aggregate = {
        key: float(np.mean([row[key] for row in rows]))
        for key in ("precision", "recall", "f1", "roc_auc")
    }
    output = ROOT / "reports/cpu_baseline_report.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# CPU Baseline Evaluation",
        "",
        "> This TF-IDF/logistic-regression baseline is a diagnostic reference, not a validated security detector. Do not use it to block merges or make security decisions.",
        "",
        "## Evaluation design",
        "",
        "Leave-one-repository-out evaluation: train on all samples from the other repository, then score the held-out repository. Exact and whitespace-normalized duplicate functions are removed before splitting. Threshold: 0.50. The two directions are reported separately because this dataset contains only two repositories.",
        "",
        "Features are word unigrams/bigrams plus character 3–5 grams. Classifier is balanced logistic regression. This is a CPU baseline, not a fine-tuned CodeBERT/GraphCodeBERT model.",
        "",
        "## Results",
        "",
        "| Held-out repo | Train rows | Test rows | Precision | Recall | F1 | ROC-AUC | TN | FP | FN | TP |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        tn, fp = row["confusion_matrix_labels_0_1"][0]
        fn, tp = row["confusion_matrix_labels_0_1"][1]
        lines.append(
            f"| {row['held_out_repo']} | {row['train_rows']} | {row['test_rows']} | "
            f"{row['precision']:.4f} | {row['recall']:.4f} | {row['f1']:.4f} | "
            f"{row['roc_auc']:.4f} | {tn} | {fp} | {fn} | {tp} |"
        )
    lines.extend([
        "",
        "## Macro average across held-out repositories",
        "",
        "| Precision | Recall | F1 | ROC-AUC |",
        "|---:|---:|---:|---:|",
        f"| {aggregate['precision']:.4f} | {aggregate['recall']:.4f} | {aggregate['f1']:.4f} | {aggregate['roc_auc']:.4f} |",
        "",
        "## Limitations",
        "",
        "- The available Devign data contains only FFmpeg and QEMU, so this is a two-repository diagnostic rather than broad held-out-repository validation.",
        "- It has no severity/CWE targets, calibration, line-level explanations, or external benchmark.",
        "- A real transformer fine-tune still requires a GPU and broader repo-level data. Keep the demo ONNX artifact and GitHub merge gate disabled until that evaluation is complete.",
        "",
    ])
    output.write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "reports/cpu_baseline_metrics.json").write_text(
        json.dumps({"folds": rows, "macro_average": aggregate}, indent=2), encoding="utf-8"
    )
    model_dir = ROOT / "training/cpu_baseline"
    model_dir.mkdir(parents=True, exist_ok=True)
    full_model = make_pipeline()
    full_model.fit([s.code for s in samples], np.asarray([s.label for s in samples], dtype=np.int64))
    joblib.dump(full_model, model_dir / "model.joblib", compress=3)
    (model_dir / "model_version.json").write_text(json.dumps({
        "model_version": "cpu-tfidf-baseline-0.1",
        "model_type": "TF-IDF word/character features + balanced logistic regression",
        "training_rows": len(samples),
        "repositories": sorted(by_repo),
        "evaluation_report": "reports/cpu_baseline_report.md",
        "warning": "Research baseline only. Weak two-repository held-out metrics; not for serving, security decisions, or merge blocking.",
    }, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Saved research-only model to {model_dir}")


if __name__ == "__main__":
    main()
