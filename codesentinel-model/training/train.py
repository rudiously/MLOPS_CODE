"""
Main training entrypoint.

Two-phase flow:
  1. K-fold CV on the train split only, to select/report stable hyperparameters
     (logged to MLflow as nested runs).
  2. Final fit on train+val combined, evaluated once on the untouched test
     split, with temperature-scaling calibration fit on val logits.

Usage:
    python training/train.py --config training/config.yaml
    python training/train.py --config training/config.yaml --smoke-test   # tiny random model, no HF download
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import yaml
from sklearn.model_selection import KFold
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
from torch.utils.data import DataLoader, Subset

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from schema import CodeSample  # noqa: E402

from model import CodeSentinelModel  # noqa: E402
from losses import FocalLoss, class_weighted_ce, multitask_loss  # noqa: E402
from dataset import VulnDataset  # noqa: E402
from calibration import TemperatureScaler  # noqa: E402

try:
    import mlflow
except ImportError:
    mlflow = None


def load_samples(path: Path) -> list[CodeSample]:
    with open(path, "r", encoding="utf-8") as f:
        return [CodeSample.from_json(line) for line in f if line.strip()]


def build_model_and_tokenizer(cfg: dict, smoke_test: bool):
    if smoke_test:
        from transformers import RobertaTokenizerFast
        model = CodeSentinelModel.from_random_config(
            num_cwe_classes=cfg["model"]["num_cwe_classes"],
            num_severity_levels=len(cfg["model"]["severity_levels"]),
            dropout=cfg["model"]["dropout"],
        )
        # Byte-level BPE with no pretrained merges — deterministic, no network.
        from tokenizers import ByteLevelBPETokenizer
        import tempfile, os
        tmp_dir = tempfile.mkdtemp()
        # minimal vocab so tokenizer works standalone without training a real BPE
        vocab = {f"tok{i}": i for i in range(500)}
        vocab.update({"<s>": 500, "</s>": 501, "<pad>": 502, "<unk>": 503, "<mask>": 504})
        with open(os.path.join(tmp_dir, "vocab.json"), "w") as f:
            json.dump(vocab, f)
        with open(os.path.join(tmp_dir, "merges.txt"), "w") as f:
            f.write("#version: 0.2\n")
        tok = ByteLevelBPETokenizer(
            os.path.join(tmp_dir, "vocab.json"), os.path.join(tmp_dir, "merges.txt")
        )

        class _WrappedTok:
            """Thin wrapper giving the fast HF-style __call__ signature used
            by dataset.py, backed by the from-scratch ByteLevelBPETokenizer."""

            def __call__(self, text, truncation, max_length, padding, return_tensors):
                enc = tok.encode(text)
                ids = enc.ids[:max_length]
                pad_id = vocab["<pad>"]
                attn = [1] * len(ids) + [0] * (max_length - len(ids))
                ids = ids + [pad_id] * (max_length - len(ids))
                return {
                    "input_ids": torch.tensor([ids]),
                    "attention_mask": torch.tensor([attn]),
                }

        return model, _WrappedTok()

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(cfg["model"]["base_model"])
    model = CodeSentinelModel(
        base_model=cfg["model"]["base_model"],
        num_cwe_classes=cfg["model"]["num_cwe_classes"],
        num_severity_levels=len(cfg["model"]["severity_levels"]),
        dropout=cfg["model"]["dropout"],
    )
    return model, tokenizer


def run_epoch(model, loader, vuln_loss_fn, optimizer, device, train: bool):
    model.train(mode=train)
    total_loss = 0.0
    all_preds, all_labels, all_probs = [], [], []

    for batch in loader:
        batch = {k: v.to(device) for k, v in batch.items()}
        with torch.set_grad_enabled(train):
            out = model(batch["input_ids"], batch["attention_mask"])
            losses = multitask_loss(
                vuln_logits=out.vuln_logits,
                vuln_targets=batch["vuln_label"],
                severity_logits=out.severity_logits,
                severity_targets=batch["severity_label"],
                severity_mask=batch["severity_mask"],
                cwe_logits=out.cwe_logits,
                cwe_targets=batch["cwe_label"],
                cwe_mask=batch["cwe_mask"],
                vuln_loss_fn=vuln_loss_fn,
            )
            if train:
                losses["total"].backward()
                optimizer.step()
                optimizer.zero_grad()

        total_loss += float(losses["total"].detach())
        probs = torch.softmax(out.vuln_logits, dim=-1)[:, 1]
        all_probs.extend(probs.detach().cpu().tolist())
        all_preds.extend(out.vuln_logits.argmax(dim=-1).detach().cpu().tolist())
        all_labels.extend(batch["vuln_label"].detach().cpu().tolist())

    precision, recall, f1, _ = precision_recall_fscore_support(
        all_labels, all_preds, average="binary", zero_division=0
    )
    try:
        auroc = roc_auc_score(all_labels, all_probs) if len(set(all_labels)) > 1 else float("nan")
    except ValueError:
        auroc = float("nan")

    return {
        "loss": total_loss / max(len(loader), 1),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "auroc": auroc,
    }


def make_loss_fn(cfg: dict, samples: list[CodeSample]) -> torch.nn.Module:
    if cfg["training"]["loss"]["type"] == "focal":
        return FocalLoss(gamma=cfg["training"]["loss"]["focal_gamma"])
    counts = {0: 0, 1: 0}
    for s in samples:
        counts[s.label] += 1
    return class_weighted_ce(counts)


def kfold_cv(cfg: dict, train_samples: list[CodeSample], tokenizer, device, smoke_test: bool) -> dict:
    k = 2 if smoke_test else cfg["training"]["k_folds"]
    kf = KFold(n_splits=k, shuffle=True, random_state=cfg["training"]["seed"])
    fold_metrics = []
    dataset = VulnDataset(train_samples, tokenizer, max_length=cfg["model"]["max_seq_length"])

    indices = np.arange(len(train_samples))
    for fold_idx, (tr_idx, va_idx) in enumerate(kf.split(indices)):
        model, _ = build_model_and_tokenizer(cfg, smoke_test)
        model.to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["training"]["learning_rate"])
        loss_fn = make_loss_fn(cfg, [train_samples[i] for i in tr_idx])

        train_loader = DataLoader(Subset(dataset, tr_idx), batch_size=cfg["training"]["batch_size"], shuffle=True)
        val_loader = DataLoader(Subset(dataset, va_idx), batch_size=cfg["training"]["batch_size"])

        epochs = 1 if smoke_test else cfg["training"]["epochs"]
        for _ in range(epochs):
            run_epoch(model, train_loader, loss_fn, optimizer, device, train=True)
        val_metrics = run_epoch(model, val_loader, loss_fn, optimizer, device, train=False)
        fold_metrics.append(val_metrics)
        print(f"[fold {fold_idx}] val f1={val_metrics['f1']:.4f} auroc={val_metrics['auroc']:.4f}")

    avg = {k_: float(np.nanmean([m[k_] for m in fold_metrics])) for k_ in fold_metrics[0]}
    return avg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("training/config.yaml"))
    parser.add_argument("--smoke-test", action="store_true",
                         help="Use a tiny random-init model + 2-fold CV + 1 epoch, no HF hub access needed.")
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    # Guard against PyYAML reading exponential notation without a decimal
    # point (e.g. "2e-5") back as a string instead of a float — fail with a
    # clear message here rather than deep inside torch.optim's lr check.
    lr = cfg["training"]["learning_rate"]
    if not isinstance(lr, (int, float)):
        raise TypeError(
            f"training.learning_rate parsed as {type(lr).__name__} ({lr!r}), not a number. "
            f"Write exponential values with a decimal point, e.g. 2.0e-5 instead of 2e-5."
        )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(cfg["training"]["seed"])

    data_dir = Path(cfg["data"]["processed_dir"])
    train_samples = load_samples(data_dir / "train.jsonl")
    val_samples = load_samples(data_dir / "val.jsonl")
    test_samples = load_samples(data_dir / "test.jsonl")
    print(f"Loaded train={len(train_samples)} val={len(val_samples)} test={len(test_samples)}")
    if not train_samples or not val_samples or not test_samples:
        raise ValueError(
            "Training requires non-empty train, validation, and test splits. "
            f"Found train={len(train_samples)}, val={len(val_samples)}, test={len(test_samples)}. "
            "Rebuild the dataset splits before starting training."
        )

    _, tokenizer = build_model_and_tokenizer(cfg, args.smoke_test)

    if mlflow is not None:
        mlflow.set_tracking_uri(cfg["mlflow"]["tracking_uri"])
        mlflow.set_experiment(cfg["mlflow"]["experiment_name"])
        run_ctx = mlflow.start_run()
    else:
        run_ctx = None
        print("mlflow not installed — proceeding without experiment tracking")

    try:
        if mlflow is not None:
            mlflow.log_params({
                "base_model": cfg["model"]["base_model"],
                "epochs": cfg["training"]["epochs"],
                "batch_size": cfg["training"]["batch_size"],
                "lr": cfg["training"]["learning_rate"],
                "loss_type": cfg["training"]["loss"]["type"],
                "smoke_test": args.smoke_test,
            })

        print("=== Phase 1: k-fold CV on train split ===")
        cv_metrics = kfold_cv(cfg, train_samples, tokenizer, device, args.smoke_test)
        print(f"CV avg metrics: {cv_metrics}")
        if mlflow is not None:
            mlflow.log_metrics({f"cv_{k}": v for k, v in cv_metrics.items()})

        print("=== Phase 2: final fit on train+val ===")
        final_train_samples = train_samples + val_samples
        model, _ = build_model_and_tokenizer(cfg, args.smoke_test)
        model.to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["training"]["learning_rate"])
        loss_fn = make_loss_fn(cfg, final_train_samples)

        train_ds = VulnDataset(
            final_train_samples, tokenizer,
            max_length=cfg["model"]["max_seq_length"],
            augment_frac=cfg["data"]["augment_frac"] if cfg["data"]["augment_train"] else 0.0,
        )
        val_ds = VulnDataset(val_samples, tokenizer, max_length=cfg["model"]["max_seq_length"])
        test_ds = VulnDataset(test_samples, tokenizer, max_length=cfg["model"]["max_seq_length"])

        train_loader = DataLoader(train_ds, batch_size=cfg["training"]["batch_size"], shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=cfg["training"]["batch_size"])
        test_loader = DataLoader(test_ds, batch_size=cfg["training"]["batch_size"])

        best_val_f1 = -1.0
        patience_left = cfg["training"]["early_stopping_patience"]
        epochs = 1 if args.smoke_test else cfg["training"]["epochs"]

        ckpt_dir = Path(cfg["output"]["checkpoint_dir"])
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        best_ckpt_path = ckpt_dir / "best_model.pt"

        for epoch in range(epochs):
            train_metrics = run_epoch(model, train_loader, loss_fn, optimizer, device, train=True)
            val_metrics = run_epoch(model, val_loader, loss_fn, optimizer, device, train=False)
            print(f"[epoch {epoch}] train_f1={train_metrics['f1']:.4f} val_f1={val_metrics['f1']:.4f}")
            if mlflow is not None:
                mlflow.log_metrics({
                    f"train_{k}": v for k, v in train_metrics.items()
                }, step=epoch)
                mlflow.log_metrics({
                    f"val_{k}": v for k, v in val_metrics.items()
                }, step=epoch)

            if val_metrics["f1"] > best_val_f1:
                best_val_f1 = val_metrics["f1"]
                patience_left = cfg["training"]["early_stopping_patience"]
                torch.save(model.state_dict(), best_ckpt_path)
            else:
                patience_left -= 1
                if patience_left <= 0:
                    print(f"Early stopping at epoch {epoch}")
                    break

        model.load_state_dict(torch.load(best_ckpt_path))

        print("=== Calibration (temperature scaling on val logits) ===")
        model.eval()
        val_logits, val_labels = [], []
        with torch.no_grad():
            for batch in val_loader:
                batch = {k: v.to(device) for k, v in batch.items()}
                out = model(batch["input_ids"], batch["attention_mask"])
                val_logits.append(out.vuln_logits.cpu())
                val_labels.append(batch["vuln_label"].cpu())
        val_logits = torch.cat(val_logits)
        val_labels = torch.cat(val_labels)

        scaler = TemperatureScaler()
        ece = scaler.fit(val_logits, val_labels)
        print(f"Calibration ECE after scaling: {ece:.4f}, temperature={float(scaler.temperature):.3f}")
        if mlflow is not None:
            mlflow.log_metric("calibration_ece", ece)
            mlflow.log_metric("temperature", float(scaler.temperature))

        print("=== Final test evaluation ===")
        test_metrics = run_epoch(model, test_loader, loss_fn, optimizer, device, train=False)
        print(f"Test metrics: {test_metrics}")
        if mlflow is not None:
            mlflow.log_metrics({f"test_{k}": v for k, v in test_metrics.items()})

        final_dir = Path(cfg["output"]["final_model_dir"])
        final_dir.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), final_dir / "model.pt")
        torch.save(scaler.state_dict(), final_dir / "temperature_scaler.pt")
        with open(final_dir / "test_metrics.json", "w") as f:
            json.dump(test_metrics, f, indent=2)

        if mlflow is not None:
            mlflow.log_artifact(str(final_dir / "test_metrics.json"))
            # MLflow's traced pt2 format is not used by our checkpoint-based exporters.
            mlflow.pytorch.log_model(
                model,
                "model",
                serialization_format="cloudpickle",
                registered_model_name=cfg["mlflow"]["registered_model_name"],
            )

        print(f"Final model + calibration saved to {final_dir}")
    finally:
        if run_ctx is not None:
            mlflow.end_run()


if __name__ == "__main__":
    main()
