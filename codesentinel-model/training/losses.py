"""
Loss functions for the multi-task setup:
  - focal loss / class-weighted CE for the imbalanced binary vuln label
  - masked cross-entropy for severity and CWE heads (only samples that
    actually have those labels contribute gradient)
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class FocalLoss(nn.Module):
    """Standard focal loss (Lin et al. 2017), for the binary vuln head.
    Down-weights easy (well-classified) examples so the model doesn't just
    learn to predict the majority class — important here since clean
    functions vastly outnumber vulnerable ones in Devign/Big-Vul."""

    def __init__(self, gamma: float = 2.0, weight: torch.Tensor | None = None):
        super().__init__()
        self.gamma = gamma
        self.weight = weight

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        ce = F.cross_entropy(logits, targets, weight=self.weight, reduction="none")
        pt = torch.exp(-ce)
        focal = ((1 - pt) ** self.gamma) * ce
        return focal.mean()


def class_weighted_ce(class_counts: dict[int, int]) -> nn.CrossEntropyLoss:
    """Builds a CE loss with inverse-frequency class weights."""
    total = sum(class_counts.values())
    n_classes = max(class_counts.keys()) + 1
    weights = torch.ones(n_classes)
    for cls, count in class_counts.items():
        weights[cls] = total / (n_classes * max(count, 1))
    return nn.CrossEntropyLoss(weight=weights)


def masked_ce(logits: torch.Tensor, targets: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """Cross-entropy computed only over rows where mask == True. Returns 0.0
    (no gradient contribution) if no rows are masked-in for this batch —
    this is how the severity/CWE heads avoid being penalized for samples
    that simply don't have those labels."""
    if mask.sum() == 0:
        return torch.tensor(0.0, device=logits.device, requires_grad=True)
    return F.cross_entropy(logits[mask], targets[mask])


def multitask_loss(
    vuln_logits: torch.Tensor,
    vuln_targets: torch.Tensor,
    severity_logits: torch.Tensor,
    severity_targets: torch.Tensor,
    severity_mask: torch.Tensor,
    cwe_logits: torch.Tensor,
    cwe_targets: torch.Tensor,
    cwe_mask: torch.Tensor,
    vuln_loss_fn: nn.Module,
    severity_weight: float = 0.3,
    cwe_weight: float = 0.3,
) -> dict[str, torch.Tensor]:
    vuln_loss = vuln_loss_fn(vuln_logits, vuln_targets)
    severity_loss = masked_ce(severity_logits, severity_targets, severity_mask)
    cwe_loss = masked_ce(cwe_logits, cwe_targets, cwe_mask)
    total = vuln_loss + severity_weight * severity_loss + cwe_weight * cwe_loss
    return {
        "total": total,
        "vuln_loss": vuln_loss.detach(),
        "severity_loss": severity_loss.detach(),
        "cwe_loss": cwe_loss.detach(),
    }
