"""
Temperature scaling (Guo et al. 2017) fit on the validation set, applied to
the vuln-classifier logits so predicted probabilities are meaningful
confidence scores. This matters specifically because CodeSentinel gates
merges — an overconfident false positive blocks a developer's PR, so the
confidence number needs to mean what it says.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class TemperatureScaler(nn.Module):
    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        return logits / self.temperature

    def fit(self, logits: torch.Tensor, labels: torch.Tensor, max_iter: int = 50) -> float:
        """Fits temperature by minimizing NLL on held-out logits/labels.
        Returns the final expected calibration error (ECE) for reporting."""
        optimizer = torch.optim.LBFGS([self.temperature], lr=0.01, max_iter=max_iter)

        def closure():
            optimizer.zero_grad()
            loss = F.cross_entropy(self.forward(logits), labels)
            loss.backward()
            return loss

        optimizer.step(closure)
        return expected_calibration_error(self.forward(logits), labels)


def expected_calibration_error(logits: torch.Tensor, labels: torch.Tensor, n_bins: int = 10) -> float:
    probs = F.softmax(logits, dim=-1)
    confidences, predictions = probs.max(dim=-1)
    accuracies = predictions.eq(labels)

    ece = torch.zeros(1, device=logits.device)
    bin_boundaries = torch.linspace(0, 1, n_bins + 1)
    for lo, hi in zip(bin_boundaries[:-1], bin_boundaries[1:]):
        in_bin = (confidences > lo) & (confidences <= hi)
        prop_in_bin = in_bin.float().mean()
        if prop_in_bin > 0:
            acc_in_bin = accuracies[in_bin].float().mean()
            conf_in_bin = confidences[in_bin].mean()
            ece += torch.abs(conf_in_bin - acc_in_bin) * prop_in_bin
    return float(ece.item())
