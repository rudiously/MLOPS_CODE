# CodeSentinel Model — Model Card

## Overview

## Demo artifact warning

`demo-synthetic-0.1` is a **PLUMBING MODEL**, trained only on tiny synthetic
smoke-test data with a randomly initialized encoder. It has no valid
vulnerability-detection accuracy, must not be used for security decisions, and
exists only to verify package and API wiring.
CodeSentinel's model core is a multi-task classifier built on a code-aware
transformer encoder (GraphCodeBERT/CodeBERT by default). It predicts:
1. **Vulnerability** (binary: vulnerable / clean)
2. **Severity** (low / medium / high / critical) — trained only where labels exist
3. **CWE category** (top-K + "other") — trained only where labels exist

Explainability is provided two ways depending on where in the stack you are:
- **Training/eval time** (`explainability/`): Integrated Gradients (primary)
  and attention rollout (cheap secondary method), both requiring the full
  PyTorch model with gradients.
- **Serving time** (`codesentinel_model/predict.py`): occlusion-based line
  attribution against the exported ONNX graph — no gradients needed, so the
  serving container only needs `onnxruntime` + a tokenizer, not the full
  training stack (torch, captum, mlflow).

This split is intentional: the heavier, more faithful attribution methods
run offline when generating the evaluation report; the lightweight method
runs online in the merge-gating path where latency and dependency footprint
matter more than attribution fidelity.

## Intended use
Flagging likely-vulnerable functions in a pull request, with a severity
estimate, a CWE guess, and the specific lines most responsible for the flag
— as one signal in a CI gate, not a sole merge/block authority. False
positives are expected; the calibration step (temperature scaling) exists
specifically so the confidence score is honest about that.

## Training data
See `data/DATASET_CARD.md` (auto-generated from whatever you actually
process) for the real numbers. Source: Devign, Big-Vul, CodeXGLUE
Defect-Detection, combined, deduplicated, and split by repository.

## Known limitations
- **C/C++ bias.** All three source datasets are overwhelmingly C/C++.
  Treat predictions on other languages as out-of-distribution.
- **Function-level vs. line-level labels.** Only Big-Vul carries line-level
  ground truth, so localization accuracy is only measured on that subset.
- **Occlusion attribution is coarser than Integrated Gradients.** The
  serving-time `predict()` line attributions are a cheap proxy (mask a line,
  see how much the vulnerability score drops), not the same fidelity as the
  IG-based attributions in the offline evaluation report. Don't expect them
  to agree exactly line-for-line.
- **Position-id computation is padding-aware in a way that matters for
  export.** RoBERTa-family models (CodeBERT/GraphCodeBERT included) compute
  position ids from `input_ids != pad_token_id`, not from a separate
  position counter. In real usage this is fine — a real tokenizer never
  emits the pad-token id (typically id `1`) as actual code content, so the
  computation is well-defined. But if you ever feed synthetic/random token
  ids into a parity check (rather than genuine tokenizer output), a token
  that happens to equal the pad-token id will be silently treated as
  padding and shift position ids in a way that can diverge from the traced
  ONNX/TorchScript graph. `export/parity_check.py` avoids this by
  excluding reserved special-token ids from its random test inputs by
  default, and has an `--include-padding` flag to explicitly test a
  realistic padded sequence (the shape production traffic actually sends).

## A genuinely subtle export gotcha (documented for whoever touches this next)
`torch.onnx.export()` (legacy TorchScript-based exporter) can leave the
source PyTorch model in **train() mode** as a side effect of tracing, even
if you called `.eval()` right before exporting. If you then run inference
on that same in-memory model object without calling `.eval()` again,
dropout is silently active again and outputs become non-deterministic and
wrong — this looks exactly like "the export is broken" when it's actually
the *original* model that's now broken. `export_onnx.py` and
`export_torchscript.py` both call `model.eval()` again immediately after
exporting to guard against this; if you refactor either script, keep that
line, and if you write new export code, do the same or restructure to
export a throwaway copy of the model.

## Evaluation
Run `evaluation/generate_report.py` after training for the full report:
precision/recall/F1/AUROC, confusion matrix, ROC/PR curves, calibration
plot + ECE, top-3 localization accuracy on the Big-Vul line-labeled subset,
and a robustness section comparing F1 on the clean test set vs. the same
set under variable-renaming/dead-code/reordering augmentation.

## What was actually validated in this environment vs. what still needs a
## real GPU + real data
This repository's containerized sandbox has no GPU and cannot reach
huggingface.co, so nothing here was trained on real Devign/Big-Vul data
with a real GraphCodeBERT checkpoint. What *was* verified, end-to-end, with
a tiny randomly-initialized encoder standing in for the real one:
- Data schema validation, deduplication, and repo-level splitting
- Focal loss, class-weighted loss, masked multi-task loss
- Temperature-scaling calibration (ECE compared before/after)
- Full training loop: k-fold CV phase + final-fit phase + early stopping
- ONNX and TorchScript export, with numerical parity confirmed against the
  original PyTorch outputs
- The `predict()` handoff function against a real exported ONNX model,
  matching the documented JSON schema

What still needs your own GPU (Colab/Kaggle/etc.) with real internet
access: downloading `microsoft/graphcodebert-base`, downloading the actual
datasets, and running training long enough to get real precision/recall/F1
numbers. Everything downstream of that (export, parity check, benchmark,
report generation) is already wired up to consume real checkpoints — swap
`--smoke-test` off and point `data.processed_dir` at your real processed
data.
