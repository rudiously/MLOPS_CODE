# CodeSentinel — Model Core (ML Engineer scope)

The ML Engineer's deliverable for the CodeSentinel CI/CD vulnerability
gatekeeper: a trained, registered multi-task model, an evaluation report,
ONNX/TorchScript exports, and a dependency-light `predict()` function ready
to hand to whoever builds the FastAPI/GitHub Action layer.

**Every module in this repo has been run and its tests pass in this
environment**, using a tiny randomly-initialized encoder in place of a
downloaded GraphCodeBERT checkpoint (this sandbox has no GPU and no
internet access to huggingface.co). See `model_card.md` for exactly what
was validated vs. what still needs your own GPU + real datasets, and for
two genuinely subtle bugs that were found and fixed in the process
(a `torch.onnx.export` train/eval-mode side effect, and a PyYAML
scientific-notation parsing gotcha).

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Quickstart: run the whole pipeline on real data

```bash
# 1. Download raw datasets (needs real internet access — Colab/Kaggle/your box)
python data/download.py --dataset all --out data/raw/

# 2. Normalize into the unified schema
python data/preprocess.py --raw-dir data/raw/ --out data/processed/all_samples.jsonl

# 3. Dedup + repo-level split (prevents leakage between train/val/test)
python data/dedup_split.py --in data/processed/all_samples.jsonl --out-dir data/processed/

# 4. Generate the dataset card
python data/dataset_card.py --processed-dir data/processed --out data/DATASET_CARD.md

# 5. Train (k-fold CV, then final fit, with MLflow tracking + calibration)
python training/train.py --config training/config.yaml

# 6. Promote to Production in the MLflow registry if it beats the current model
python mlflow/promote_model.py --model-name codesentinel-vuln-classifier

# 7. Generate the full evaluation report (metrics, plots, localization, robustness)
python evaluation/generate_report.py --config training/config.yaml

# 8. Export for serving
python export/export_onnx.py --checkpoint training/final_model/model.pt --config training/config.yaml
python export/export_torchscript.py --checkpoint training/final_model/model.pt --config training/config.yaml

# 9. Verify the exports are numerically faithful to the trained model
python export/parity_check.py \
  --pytorch-model training/final_model/model.pt \
  --onnx-model export/artifacts/model.onnx \
  --torchscript-model export/artifacts/model_ts.pt \
  --config training/config.yaml --include-padding

# 10. Benchmark latency/throughput to help Person 2 pick a serving format
python export/benchmark.py \
  --pytorch-model training/final_model/model.pt \
  --onnx-model export/artifacts/model.onnx \
  --torchscript-model export/artifacts/model_ts.pt \
  --config training/config.yaml
```

## Quickstart: verify the pipeline works right now, with no GPU/internet

```bash
pytest tests/ -v
```

All 19 tests pass in well under a minute — including
`tests/test_smoke_pipeline.py`, which runs data generation, dedup/split,
2-fold CV, final training, calibration, and checkpoint saving end-to-end
using a tiny random-init model. This is the same "meta" CI touch the
project spec calls for: the vulnerability-scanning tool has clean CI on
itself (`.github/workflows/ci.yml` runs this on every push).

## Handoff to Person 2 (serving layer)

### Local demo artifacts — PLUMBING MODEL ONLY

Run `python scripts/build_demo_artifacts.py` to build a CPU-only serving bundle
without downloading Hugging Face weights. It creates `model.onnx`, `model_ts.pt`,
a local tokenizer, CWE vocabulary, and version metadata in
`codesentinel_model/artifacts/`. Its version is `demo-synthetic-0.1` and it was
trained only on tiny synthetic smoke-test data with a randomly initialized
encoder. It is **not a real vulnerability detector**, has no valid accuracy
claim, and must never be used for security decisions. It exists only to prove
the packaging and API plumbing end to end.

```python
from codesentinel_model import predict

result = predict(open("suspicious_function.c").read())
# {
#   "is_vulnerable": True,
#   "confidence": 0.87,
#   "severity": "high",
#   "predicted_cwe": [{"cwe_id": "CWE-119", "score": 0.62}, ...],
#   "line_attributions": [{"line": 4, "score": 0.31, "snippet": "strcpy(buf, input);"}, ...],
#   "model_version": "unversioned"
# }
```

Install just this package into a slim serving container:
```bash
pip install -e .
```
It depends only on `onnxruntime`, `transformers` (for the tokenizer), and
`numpy` — no torch, no MLflow, no captum. Output shape is documented and
machine-checkable at `codesentinel_model/output_schema.json`.

For a real service handling many requests, use `load_model()` once and
reuse the returned `CodeSentinelPredictor` instead of calling the
module-level `predict()` repeatedly (which lazily builds one under the
hood but is meant for scripts/tests, not a hot path).

## Repo structure

```
codesentinel-model/
  data/                  # download, preprocess, dedup/split, augment, dataset card
  training/              # model, losses, dataset, calibration, train.py, config.yaml
  explainability/        # Integrated Gradients, attention rollout, localization eval
  export/                # ONNX / TorchScript export, parity check, benchmark
  evaluation/            # auto-generated evaluation report
  codesentinel_model/    # installable predict() package — the Person 2 handoff
  mlflow/                # model promotion gate
  reports/               # generated evaluation_report.md + plots land here
  tests/                 # unit tests + full-pipeline smoke test
  .github/workflows/     # CI: smoke test + lint on every push
```

## What to change for your actual run
- `training/config.yaml`: swap `base_model` to `microsoft/codebert-base` or
  a distilled model if compute is tight; adjust `epochs`/`batch_size` to
  your GPU's memory.
- Everything defaults to CPU-safe settings for the smoke test; real
  training will auto-detect and use CUDA if `torch.cuda.is_available()`.

## Real training checklist

Use a GPU runtime. The included Colab notebook assumes a free T4 with 16 GB
VRAM and starts with `batch_size: 8`, gradient accumulation of 2, and 3 epochs.
Those values are an assumption: reduce the batch size or epochs if the available
GPU or session time differs. After the real run, download the generated artifact
zip into `codesentinel_model/artifacts/`, replace the plumbing bundle, and rebuild
the API Docker image. A real GPU/data training run is required before making any
security-performance claim.
