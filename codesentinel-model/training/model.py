"""
Multi-task model built on top of a pretrained code-transformer encoder
(GraphCodeBERT / CodeBERT / any AutoModel-compatible checkpoint).

Three heads share one encoder:
  1. binary vulnerability classifier   (always active)
  2. severity ordinal head             (low/medium/high/critical)
  3. CWE multi-class head              (top-K CWEs + "other"), masked loss
     for samples with no CWE label

Design note: heads 2 and 3 are trained with masked loss so that samples
without severity/CWE labels (most of Devign/CodeXGLUE) don't contribute
gradient to those heads — only Big-Vul's richer labels do. This lets us
use the full combined dataset for the primary classification task while
still getting a meaningfully trained severity/CWE head from the subset
that has it.
"""
from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn
from transformers import AutoModel, AutoConfig


@dataclass
class ModelOutput:
    vuln_logits: torch.Tensor          # (B, 2)
    severity_logits: torch.Tensor      # (B, num_severity_levels)
    cwe_logits: torch.Tensor           # (B, num_cwe_classes + 1)  [+1 = "other"]
    hidden_states: torch.Tensor        # (B, T, H) — for explainability


class CodeSentinelModel(nn.Module):
    def __init__(
        self,
        base_model: str = "microsoft/graphcodebert-base",
        num_cwe_classes: int = 20,
        num_severity_levels: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.config = AutoConfig.from_pretrained(base_model)
        self.encoder = AutoModel.from_pretrained(base_model)
        hidden = self.config.hidden_size

        self.dropout = nn.Dropout(dropout)
        self.vuln_head = nn.Linear(hidden, 2)
        self.severity_head = nn.Linear(hidden, num_severity_levels)
        self.cwe_head = nn.Linear(hidden, num_cwe_classes + 1)  # +1 = "other/unknown"

    @classmethod
    def from_random_config(
        cls,
        num_cwe_classes: int = 20,
        num_severity_levels: int = 4,
        dropout: float = 0.1,
        hidden_size: int = 64,
        num_layers: int = 2,
        vocab_size: int = 5000,
    ) -> "CodeSentinelModel":
        """Builds a tiny, randomly-initialized encoder with the same interface
        as a real pretrained checkpoint — used for CI smoke tests and local
        pipeline validation where we have no network access to the HF hub.
        Never use this for real evaluation numbers."""
        from transformers import RobertaConfig, RobertaModel

        obj = cls.__new__(cls)
        nn.Module.__init__(obj)
        obj.config = RobertaConfig(
            vocab_size=vocab_size,
            hidden_size=hidden_size,
            num_hidden_layers=num_layers,
            num_attention_heads=2,
            intermediate_size=hidden_size * 2,
            max_position_embeddings=514,
        )
        obj.encoder = RobertaModel(obj.config)
        obj.dropout = nn.Dropout(dropout)
        obj.vuln_head = nn.Linear(hidden_size, 2)
        obj.severity_head = nn.Linear(hidden_size, num_severity_levels)
        obj.cwe_head = nn.Linear(hidden_size, num_cwe_classes + 1)
        return obj

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> ModelOutput:
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        hidden_states = out.last_hidden_state          # (B, T, H)
        pooled = self.dropout(hidden_states[:, 0, :])  # CLS token

        return ModelOutput(
            vuln_logits=self.vuln_head(pooled),
            severity_logits=self.severity_head(pooled),
            cwe_logits=self.cwe_head(pooled),
            hidden_states=hidden_states,
        )
