"""
Runs the ENTIRE pipeline — synthetic data generation, dedup/split, a
2-fold CV + final fit with the tiny random-config model, calibration, and
ONNX export — in well under a minute, with no network access required. This
is the meta touch matching the project's own theme: CodeSentinel gets CI on
itself. If this test is green, the plumbing between every module is sound;
real-scale numbers still require a GPU + the real datasets + a downloaded
base-model checkpoint.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def make_synthetic_dataset(n: int = 40) -> list[dict]:
    vulnerable_templates = [
        'void f{i}(char *input) {{ char buf[8]; strcpy(buf, input); }}',
        'void f{i}(int n) {{ int arr[10]; arr[n] = 1; }}',
        'char *f{i}(char *s) {{ return strcat(s, "x"); }}',
    ]
    clean_templates = [
        'int f{i}(int a, int b) {{ return a + b; }}',
        'void f{i}(char *dst, const char *src, size_t n) {{ strncpy(dst, src, n); }}',
        'int f{i}(int *arr, int len) {{ int sum = 0; for (int j = 0; j < len; j++) sum += arr[j]; return sum; }}',
    ]
    samples = []
    for i in range(n):
        is_vuln = i % 2 == 0
        template = vulnerable_templates[i % len(vulnerable_templates)] if is_vuln else clean_templates[i % len(clean_templates)]
        samples.append({
            "id": f"synthetic-{i}",
            "source_dataset": "synthetic",
            "language": "c",
            "repo": f"repo{i % 6}",
            "code": template.format(i=i),
            "label": 1 if is_vuln else 0,
            "severity": "high" if is_vuln else None,
            "cwe_id": "CWE-119" if is_vuln else None,
            "vulnerable_lines": [1] if is_vuln else [],
            "commit_sha": None,
            "function_name": f"f{i}",
        })
    return samples


def test_full_pipeline_smoke(tmp_path):
    sys.path.insert(0, str(REPO_ROOT / "data"))
    from schema import CodeSample
    from dedup_split import dedup, repo_level_split, write_jsonl

    raw_samples = [CodeSample(**s) for s in make_synthetic_dataset(40)]
    deduped, _ = dedup(raw_samples)
    train, val, test = repo_level_split(deduped, test_frac=0.2, val_frac=0.2, seed=0)
    assert len(train) > 0 and len(val) > 0 and len(test) > 0

    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    write_jsonl(train, processed_dir / "train.jsonl")
    write_jsonl(val, processed_dir / "val.jsonl")
    write_jsonl(test, processed_dir / "test.jsonl")

    config_text = f"""
model:
  base_model: microsoft/graphcodebert-base
  max_seq_length: 32
  num_cwe_classes: 3
  severity_levels: [low, medium, high, critical]
  dropout: 0.1
data:
  processed_dir: {processed_dir}
  augment_train: true
  augment_frac: 0.2
training:
  epochs: 1
  batch_size: 4
  learning_rate: 2.0e-4
  weight_decay: 0.01
  warmup_ratio: 0.06
  seed: 0
  k_folds: 2
  loss:
    type: focal
    focal_gamma: 2.0
  early_stopping_patience: 1
  gradient_accumulation_steps: 1
  fp16: false
calibration:
  method: temperature_scaling
  fit_on: val
mlflow:
  tracking_uri: {tmp_path / "mlruns"}
  experiment_name: smoke-test
  registered_model_name: smoke-test-model
output:
  checkpoint_dir: {tmp_path / "checkpoints"}
  final_model_dir: {tmp_path / "final_model"}
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_text)

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "training" / "train.py"),
         "--config", str(config_path), "--smoke-test"],
        capture_output=True, text=True, timeout=120,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, f"train.py failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    assert (tmp_path / "final_model" / "model.pt").exists()
    assert (tmp_path / "final_model" / "test_metrics.json").exists()
