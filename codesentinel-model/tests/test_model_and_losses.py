import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))

from model import CodeSentinelModel  # noqa: E402
from losses import FocalLoss, class_weighted_ce, masked_ce, multitask_loss  # noqa: E402
from calibration import TemperatureScaler, expected_calibration_error  # noqa: E402


def test_random_config_model_forward_shapes():
    model = CodeSentinelModel.from_random_config(
        num_cwe_classes=5, num_severity_levels=4, hidden_size=32, num_layers=1, vocab_size=200
    )
    input_ids = torch.randint(0, 200, (2, 16))
    attention_mask = torch.ones((2, 16), dtype=torch.long)
    out = model(input_ids, attention_mask)

    assert out.vuln_logits.shape == (2, 2)
    assert out.severity_logits.shape == (2, 4)
    assert out.cwe_logits.shape == (2, 6)  # 5 + "other"
    assert out.hidden_states.shape[0] == 2


def test_focal_loss_runs_and_reduces_to_scalar():
    loss_fn = FocalLoss(gamma=2.0)
    logits = torch.randn(8, 2)
    targets = torch.randint(0, 2, (8,))
    loss = loss_fn(logits, targets)
    assert loss.dim() == 0
    assert loss.item() >= 0


def test_class_weighted_ce_upweights_minority_class():
    loss_fn = class_weighted_ce({0: 90, 1: 10})
    assert loss_fn.weight[1] > loss_fn.weight[0]


def test_masked_ce_returns_zero_when_mask_all_false():
    logits = torch.randn(4, 3)
    targets = torch.randint(0, 3, (4,))
    mask = torch.zeros(4, dtype=torch.bool)
    loss = masked_ce(logits, targets, mask)
    assert loss.item() == 0.0


def test_multitask_loss_combines_all_three_heads():
    vuln_logits = torch.randn(4, 2)
    vuln_targets = torch.randint(0, 2, (4,))
    severity_logits = torch.randn(4, 4)
    severity_targets = torch.randint(0, 4, (4,))
    severity_mask = torch.tensor([True, False, True, False])
    cwe_logits = torch.randn(4, 6)
    cwe_targets = torch.randint(0, 6, (4,))
    cwe_mask = torch.tensor([True, True, False, False])

    result = multitask_loss(
        vuln_logits, vuln_targets, severity_logits, severity_targets, severity_mask,
        cwe_logits, cwe_targets, cwe_mask, vuln_loss_fn=FocalLoss(),
    )
    assert "total" in result
    assert result["total"].item() >= 0


def test_temperature_scaler_reduces_or_maintains_ece():
    logits = torch.randn(200, 2) * 3  # overconfident-ish logits
    labels = torch.randint(0, 2, (200,))
    ece_before = expected_calibration_error(logits, labels)

    scaler = TemperatureScaler()
    ece_after = scaler.fit(logits, labels)
    assert ece_after <= ece_before + 1e-3  # scaling should not make it meaningfully worse
