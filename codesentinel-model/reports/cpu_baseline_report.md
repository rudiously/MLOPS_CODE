# CPU Baseline Evaluation

> This TF-IDF/logistic-regression baseline is a diagnostic reference, not a validated security detector. Do not use it to block merges or make security decisions.

## Evaluation design

Leave-one-repository-out evaluation: train on all samples from the other repository, then score the held-out repository. Exact and whitespace-normalized duplicate functions are removed before splitting. Threshold: 0.50. The two directions are reported separately because this dataset contains only two repositories.

Features are word unigrams/bigrams plus character 3–5 grams. Classifier is balanced logistic regression. This is a CPU baseline, not a fine-tuned CodeBERT/GraphCodeBERT model.

## Results

| Held-out repo | Train rows | Test rows | Precision | Recall | F1 | ROC-AUC | TN | FP | FN | TP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FFmpeg | 17521 | 9707 | 0.5496 | 0.4353 | 0.4858 | 0.5442 | 2994 | 1765 | 2794 | 2154 |
| qemu | 9707 | 17521 | 0.4530 | 0.4151 | 0.4332 | 0.5260 | 6321 | 3739 | 4364 | 3097 |

## Macro average across held-out repositories

| Precision | Recall | F1 | ROC-AUC |
|---:|---:|---:|---:|
| 0.5013 | 0.4252 | 0.4595 | 0.5351 |

## Limitations

- The available Devign data contains only FFmpeg and QEMU, so this is a two-repository diagnostic rather than broad held-out-repository validation.
- It has no severity/CWE targets, calibration, line-level explanations, or external benchmark.
- A real transformer fine-tune still requires a GPU and broader repo-level data. Keep the demo ONNX artifact and GitHub merge gate disabled until that evaluation is complete.
