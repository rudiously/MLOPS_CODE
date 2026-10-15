"""
Torch Dataset that turns a list of CodeSample into tokenized tensors plus
the three label tensors (vuln, severity, cwe) and their masks.
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch
from torch.utils.data import Dataset

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from schema import CodeSample, SEVERITY_LEVELS  # noqa: E402
from augment import augment as augment_code  # noqa: E402


class VulnDataset(Dataset):
    def __init__(
        self,
        samples: list[CodeSample],
        tokenizer,
        max_length: int = 512,
        cwe_vocab: dict[str, int] | None = None,
        augment_frac: float = 0.0,
        seed: int = 42,
    ):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.severity_to_idx = {s: i for i, s in enumerate(SEVERITY_LEVELS)}
        self.cwe_vocab = cwe_vocab or self._build_cwe_vocab(samples)
        self.augment_frac = augment_frac
        self.seed = seed

    @staticmethod
    def _build_cwe_vocab(samples: list[CodeSample], top_k: int = 20) -> dict[str, int]:
        from collections import Counter
        counts = Counter(s.cwe_id for s in samples if s.cwe_id)
        top = [cwe for cwe, _ in counts.most_common(top_k)]
        vocab = {cwe: i for i, cwe in enumerate(top)}
        vocab["__other__"] = len(vocab)
        return vocab

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict:
        sample = self.samples[idx]
        code = sample.code
        if self.augment_frac > 0:
            import random
            if random.Random(self.seed + idx).random() < self.augment_frac:
                code = augment_code(code, seed=self.seed + idx)

        enc = self.tokenizer(
            code,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )

        severity_idx = self.severity_to_idx.get(sample.severity, -1)
        severity_mask = severity_idx != -1
        cwe_idx = self.cwe_vocab.get(sample.cwe_id, self.cwe_vocab["__other__"]) if sample.cwe_id else -1
        cwe_mask = sample.cwe_id is not None

        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "vuln_label": torch.tensor(sample.label, dtype=torch.long),
            "severity_label": torch.tensor(max(severity_idx, 0), dtype=torch.long),
            "severity_mask": torch.tensor(severity_mask, dtype=torch.bool),
            "cwe_label": torch.tensor(max(cwe_idx, 0), dtype=torch.long),
            "cwe_mask": torch.tensor(cwe_mask, dtype=torch.bool),
        }
