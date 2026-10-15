"""
Generates reports/evaluation_report.md after training: dataset summary,
per-class metrics, confusion matrix, ROC/PR curves, calibration plot,
localization accuracy, per-CWE breakdown, and a robustness section
(F1 under adversarial augmentation vs. clean test set).

Usage:
    python evaluation/generate_report.py --config training/config.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import yaml
from sklearn.metrics import (
    confusion_matrix, roc_curve, auc, precision_recall_curve,
    precision_recall_fscore_support,
)
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "explainability"))
from schema import CodeSample  # noqa: E402
from augment import augment as augment_code  # noqa: E402
from model import CodeSentinelModel  # noqa: E402
from dataset import VulnDataset  # noqa: E402
from attributions import compute_token_attributions, aggregate_to_lines  # noqa: E402
from localization_eval import evaluate_localization  # noqa: E402


def load_samples(path: Path) -> list[CodeSample]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [CodeSample.from_json(line) for line in f if line.strip()]


def get_predictions(model, loader, device) -> dict:
    model.eval()
    all_labels, all_preds, all_probs = [], [], []
    with torch.no_grad():
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            out = model(batch["input_ids"], batch["attention_mask"])
            probs = torch.softmax(out.vuln_logits, dim=-1)[:, 1]
            all_probs.extend(probs.cpu().tolist())
            all_preds.extend(out.vuln_logits.argmax(dim=-1).cpu().tolist())
            all_labels.extend(batch["vuln_label"].cpu().tolist())
    return {"labels": all_labels, "preds": all_preds, "probs": all_probs}


def plot_confusion_matrix(labels, preds, out_path: Path) -> None:
    cm = confusion_matrix(labels, preds)
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.imshow(cm, cmap="Blues")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["clean", "vulnerable"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["clean", "vulnerable"])
    ax.set_title("Confusion Matrix (test set)")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_roc_pr(labels, probs, out_dir: Path) -> dict:
    fpr, tpr, _ = roc_curve(labels, probs)
    roc_auc = auc(fpr, tpr)
    fig, ax = plt.subplots()
    ax.plot(fpr, tpr, label=f"AUROC={roc_auc:.3f}")
    ax.plot([0, 1], [0, 1], "--", color="gray")
    ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve"); ax.legend()
    fig.savefig(out_dir / "roc_curve.png")
    plt.close(fig)

    precision, recall, _ = precision_recall_curve(labels, probs)
    fig, ax = plt.subplots()
    ax.plot(recall, precision)
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall Curve")
    fig.savefig(out_dir / "pr_curve.png")
    plt.close(fig)

    return {"auroc": float(roc_auc)}


def plot_calibration(labels, probs, out_path: Path, n_bins: int = 10) -> float:
    labels = np.array(labels); probs = np.array(probs)
    bins = np.linspace(0, 1, n_bins + 1)
    bin_acc, bin_conf = [], []
    ece = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        in_bin = (probs > lo) & (probs <= hi)
        if in_bin.sum() > 0:
            acc = labels[in_bin].mean()
            conf = probs[in_bin].mean()
            bin_acc.append(acc); bin_conf.append(conf)
            ece += abs(acc - conf) * in_bin.mean()
        else:
            bin_acc.append(0); bin_conf.append((lo + hi) / 2)

    fig, ax = plt.subplots()
    ax.plot(bin_conf, bin_acc, marker="o", label="Model")
    ax.plot([0, 1], [0, 1], "--", color="gray", label="Perfect calibration")
    ax.set_xlabel("Confidence"); ax.set_ylabel("Accuracy")
    ax.set_title(f"Calibration Plot (ECE={ece:.4f})")
    ax.legend()
    fig.savefig(out_path)
    plt.close(fig)
    return float(ece)


def robustness_eval(model, tokenizer, samples, device, cfg) -> dict:
    """Runs the test set through adversarial augmentation and reports the
    F1 delta vs. the clean test set — the robustness section."""
    clean_ds = VulnDataset(samples, tokenizer, max_length=cfg["model"]["max_seq_length"])
    clean_loader = DataLoader(clean_ds, batch_size=cfg["training"]["batch_size"])
    clean_preds = get_predictions(model, clean_loader, device)
    _, _, clean_f1, _ = precision_recall_fscore_support(
        clean_preds["labels"], clean_preds["preds"], average="binary", zero_division=0
    )

    augmented_samples = []
    for s in samples:
        s2 = CodeSample(**{**s.__dict__, "code": augment_code(s.code, seed=42)})
        augmented_samples.append(s2)
    aug_ds = VulnDataset(augmented_samples, tokenizer, max_length=cfg["model"]["max_seq_length"])
    aug_loader = DataLoader(aug_ds, batch_size=cfg["training"]["batch_size"])
    aug_preds = get_predictions(model, aug_loader, device)
    _, _, aug_f1, _ = precision_recall_fscore_support(
        aug_preds["labels"], aug_preds["preds"], average="binary", zero_division=0
    )

    return {
        "clean_f1": float(clean_f1),
        "augmented_f1": float(aug_f1),
        "f1_drop": float(clean_f1 - aug_f1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("training/config.yaml"))
    parser.add_argument("--out-dir", type=Path, default=Path("reports"))
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    args.out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    test_samples = load_samples(Path(cfg["data"]["processed_dir"]) / "test.jsonl")
    if not test_samples:
        print("No test samples found — run the data pipeline and training first.")
        return

    from train import build_model_and_tokenizer  # noqa: E402
    model, tokenizer = build_model_and_tokenizer(cfg, args.smoke_test)
    final_dir = Path(cfg["output"]["final_model_dir"])
    ckpt = final_dir / "model.pt"
    if ckpt.exists() and not args.smoke_test:
        model.load_state_dict(torch.load(ckpt, map_location="cpu"))
    model.to(device)

    test_ds = VulnDataset(test_samples, tokenizer, max_length=cfg["model"]["max_seq_length"])
    test_loader = DataLoader(test_ds, batch_size=cfg["training"]["batch_size"])
    preds = get_predictions(model, test_loader, device)

    precision, recall, f1, _ = precision_recall_fscore_support(
        preds["labels"], preds["preds"], average="binary", zero_division=0
    )

    plot_confusion_matrix(preds["labels"], preds["preds"], args.out_dir / "confusion_matrix.png")
    roc_metrics = plot_roc_pr(preds["labels"], preds["probs"], args.out_dir)
    ece = plot_calibration(preds["labels"], preds["probs"], args.out_dir / "calibration_plot.png")
    robustness = robustness_eval(model, tokenizer, test_samples, device, cfg)

    # Localization accuracy on samples that have ground-truth vulnerable lines
    localization_samples = [s for s in test_samples if s.vulnerable_lines and s.label == 1]
    loc_input = []
    for s in localization_samples[:50]:  # cap for report generation speed
        token_attrs = compute_token_attributions(model, tokenizer, s.code, device)
        line_attrs = aggregate_to_lines(s.code, token_attrs, tokenizer)
        loc_input.append((s, line_attrs))
    localization_result = evaluate_localization(loc_input, k=3) if loc_input else {
        "localization_accuracy": None, "n_evaluated": 0
    }

    report = f"""# CodeSentinel Model — Evaluation Report

## Classification performance (test set, n={len(test_samples)})
- Precision: **{precision:.4f}**
- Recall: **{recall:.4f}**
- F1: **{f1:.4f}**
- AUROC: **{roc_metrics['auroc']:.4f}**

![Confusion Matrix](confusion_matrix.png)
![ROC Curve](roc_curve.png)
![PR Curve](pr_curve.png)

## Calibration
- Expected Calibration Error: **{ece:.4f}**

![Calibration Plot](calibration_plot.png)

## Explainability: localization accuracy
- Evaluated on {localization_result['n_evaluated']} samples with ground-truth vulnerable line numbers (Big-Vul subset).
- Top-3 localization accuracy: **{localization_result['localization_accuracy']}**
  (fraction of samples where at least one of the model's top-3 attributed
  lines matches an actual vulnerable line)

## Robustness under adversarial augmentation
- Clean test F1: **{robustness['clean_f1']:.4f}**
- F1 under variable-renaming / dead-code / reordering augmentation: **{robustness['augmented_f1']:.4f}**
- F1 drop: **{robustness['f1_drop']:.4f}**

## Known failure modes
- Languages outside C/C++ are underrepresented in training data (see
  data/DATASET_CARD.md) — treat non-C/C++ predictions as low-confidence
  until a language-specific eval is added.
- Very short snippets (a handful of tokens) give the attention/IG methods
  little signal to distinguish real risk from noise — line attributions
  for these should be treated as weak signal only.
- Localization accuracy is only measured against Big-Vul's line-level
  labels since Devign/CodeXGLUE are function-level only.
"""
    (args.out_dir / "evaluation_report.md").write_text(report)
    with open(args.out_dir / "metrics.json", "w") as f:
        json.dump({
            "precision": precision, "recall": recall, "f1": f1,
            "auroc": roc_metrics["auroc"], "ece": ece,
            "localization": localization_result, "robustness": robustness,
        }, f, indent=2)

    print(f"Report written to {args.out_dir / 'evaluation_report.md'}")


if __name__ == "__main__":
    main()
