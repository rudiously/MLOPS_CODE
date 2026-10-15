"""
The handoff artifact for Person 2 (FastAPI/TorchServe + GitHub Action owner).

This module deliberately has NO dependency on torch training internals,
MLflow, or Captum — only `onnxruntime` + a tokenizer, so Person 2 can
`pip install -e .` this package alone into a slim serving container.

Explainability here uses occlusion (line-masking) rather than Integrated
Gradients: it needs only forward passes through the exported ONNX graph, no
gradients, which is what makes a dependency-light runtime possible. It is a
coarser attribution than the IG/attention-rollout methods used in the
training-time evaluation report (see explainability/), but it's the right
trade-off for a low-latency PR-gating service — see model_card.md for the
comparison.

Usage:
    from codesentinel_model import predict
    result = predict(open("some_function.c").read())
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

SEVERITY_LEVELS = ["low", "medium", "high", "critical"]

DEFAULT_MODEL_DIR = Path(__file__).resolve().parent / "artifacts"


@dataclass
class PredictorConfig:
    model_path: Path = DEFAULT_MODEL_DIR / "model.onnx"
    # Artifact-local tokenizer keeps the installed service fully offline.
    tokenizer_name_or_path: str = str(DEFAULT_MODEL_DIR / "tokenizer")
    cwe_vocab_path: Path = DEFAULT_MODEL_DIR / "cwe_vocab.json"
    max_length: int = 512
    model_version: str = "demo-synthetic-0.1"
    top_k_cwe: int = 3
    top_k_lines: int = 5


class CodeSentinelPredictor:
    """Loads the exported ONNX model once and serves predict() calls.
    Instantiate this yourself (and reuse the instance) if you're serving
    many requests — the module-level `predict()` convenience function
    creates a new session on every call, which is fine for scripts/tests
    but wasteful for a running service."""

    def __init__(self, config: Optional[PredictorConfig] = None):
        self.config = config or PredictorConfig()
        self._session = None
        self._tokenizer = None
        self._cwe_vocab: dict[str, int] = {}
        self._idx_to_cwe: dict[int, str] = {}
        self._load()

    def _load(self) -> None:
        import onnxruntime as ort
        from transformers import AutoTokenizer

        if not self.config.model_path.exists():
            raise FileNotFoundError(
                f"No exported model found at {self.config.model_path}. "
                "Run export/export_onnx.py first (see the ML Engineer README)."
            )
        self._session = ort.InferenceSession(str(self.config.model_path))
        self._tokenizer = AutoTokenizer.from_pretrained(self.config.tokenizer_name_or_path)
        version_path = DEFAULT_MODEL_DIR / "model_version.json"
        if version_path.exists():
            self.config.model_version = json.loads(version_path.read_text(encoding="utf-8"))["model_version"]

        if self.config.cwe_vocab_path.exists():
            with open(self.config.cwe_vocab_path) as f:
                self._cwe_vocab = json.load(f)
            self._idx_to_cwe = {v: k for k, v in self._cwe_vocab.items()}

    def _tokenize(self, code: str) -> dict:
        enc = self._tokenizer(
            code, truncation=True, max_length=self.config.max_length,
            padding="max_length", return_tensors="np",
        )
        return {
            "input_ids": enc["input_ids"].astype(np.int64),
            "attention_mask": enc["attention_mask"].astype(np.int64),
        }

    def _forward(self, code: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        inputs = self._tokenize(code)
        vuln_logits, severity_logits, cwe_logits = self._session.run(
            ["vuln_logits", "severity_logits", "cwe_logits"], inputs
        )
        return vuln_logits, severity_logits, cwe_logits

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return e / e.sum(axis=-1, keepdims=True)

    def _line_attributions_by_occlusion(self, code: str, base_vuln_prob: float) -> list[dict]:
        """Masks each non-blank line out (replaces with a comment placeholder)
        and measures the drop in predicted vulnerability probability. Lines
        whose removal drops the score the most are the most "responsible" for
        the flag — a cheap, gradient-free proxy for line-level attribution."""
        lines = code.split("\n")
        scores = []
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            occluded_lines = lines.copy()
            occluded_lines[i] = "// masked"
            occluded_code = "\n".join(occluded_lines)
            vuln_logits, _, _ = self._forward(occluded_code)
            occluded_prob = float(self._softmax(vuln_logits)[0, 1])
            scores.append({
                "line": i + 1,
                "score": round(base_vuln_prob - occluded_prob, 4),
                "snippet": line.strip(),
            })
        scores.sort(key=lambda s: abs(s["score"]), reverse=True)
        return scores[: self.config.top_k_lines]

    def predict(self, code_snippet: str, language: str = "auto", explain: bool = True) -> dict:
        vuln_logits, severity_logits, cwe_logits = self._forward(code_snippet)
        vuln_probs = self._softmax(vuln_logits)[0]
        is_vulnerable = bool(np.argmax(vuln_probs) == 1)
        confidence = float(vuln_probs[1] if is_vulnerable else vuln_probs[0])

        severity_probs = self._softmax(severity_logits)[0]
        severity = SEVERITY_LEVELS[int(np.argmax(severity_probs))]

        cwe_probs = self._softmax(cwe_logits)[0]
        top_k_idx = np.argsort(cwe_probs)[::-1][: self.config.top_k_cwe]
        predicted_cwe = [
            {"cwe_id": self._idx_to_cwe.get(int(idx), "__other__"), "score": float(cwe_probs[idx])}
            for idx in top_k_idx
        ]

        line_attributions = []
        if explain and is_vulnerable:
            line_attributions = self._line_attributions_by_occlusion(code_snippet, float(vuln_probs[1]))

        return {
            "is_vulnerable": is_vulnerable,
            "confidence": round(confidence, 4),
            "severity": severity,
            "predicted_cwe": predicted_cwe,
            "line_attributions": line_attributions,
            "model_version": self.config.model_version,
        }


_default_predictor: Optional[CodeSentinelPredictor] = None


def load_model(config: Optional[PredictorConfig] = None) -> CodeSentinelPredictor:
    """Explicit loader — prefer this in a long-running service so the ONNX
    session and tokenizer are loaded once, not on every request."""
    return CodeSentinelPredictor(config)


def predict(code_snippet: str, language: str = "auto") -> dict:
    """Convenience one-shot function matching the exact contract handed off
    to Person 2:

        def predict(code_snippet: str, language: str = "auto") -> dict

    Lazily initializes a module-level predictor on first call and reuses it
    afterward. For a high-throughput service, use load_model() directly and
    keep the returned CodeSentinelPredictor alive instead.
    """
    global _default_predictor
    if _default_predictor is None:
        _default_predictor = load_model()
    return _default_predictor.predict(code_snippet, language=language)
