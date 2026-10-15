"""
Attention rollout (Abnar & Zuidema 2020) — a much cheaper secondary
explainability method than Integrated Gradients. Useful when latency
matters more than attribution fidelity (e.g. a "fast mode" for large PRs
with many changed functions), at the cost of being a rougher proxy for
which tokens actually drove the prediction.
"""
from __future__ import annotations

import torch


def compute_attention_rollout(
    model,
    tokenizer,
    code: str,
    device: torch.device,
    max_length: int = 512,
    discard_ratio: float = 0.1,
) -> list[tuple[str, float]]:
    """Runs a forward pass with attentions returned, then rolls attention
    matrices across layers (residual-aware) to get a single relevance score
    per token relative to the CLS token."""
    model.eval()
    enc = tokenizer(code, truncation=True, max_length=max_length, padding="max_length", return_tensors="pt")
    input_ids = enc["input_ids"].to(device)
    attention_mask = enc["attention_mask"].to(device)

    with torch.no_grad():
        out = model.encoder(
            input_ids=input_ids, attention_mask=attention_mask, output_attentions=True
        )
    attentions = out.attentions  # tuple of (B, heads, T, T), one per layer

    result = _rollout(attentions, discard_ratio=discard_ratio)
    cls_relevance = result[0, 0, :]  # relevance of every token w.r.t. CLS

    tokens = tokenizer.convert_ids_to_tokens(input_ids.squeeze(0).cpu().tolist())
    mask = attention_mask.squeeze(0).cpu().tolist()

    return [
        (tok, float(score))
        for tok, score, m in zip(tokens, cls_relevance.cpu().tolist(), mask)
        if m == 1
    ]


def _rollout(attentions: tuple[torch.Tensor, ...], discard_ratio: float) -> torch.Tensor:
    result = None
    for attn in attentions:
        # average over heads
        attn_avg = attn.mean(dim=1)  # (B, T, T)
        if discard_ratio > 0:
            flat = attn_avg.view(attn_avg.size(0), -1)
            n_discard = int(flat.size(-1) * discard_ratio)
            if n_discard > 0:
                _, idx = torch.topk(flat, n_discard, dim=-1, largest=False)
                flat.scatter_(-1, idx, 0.0)

        identity = torch.eye(attn_avg.size(-1), device=attn_avg.device).unsqueeze(0)
        attn_avg = (attn_avg + identity) / 2  # residual connection
        attn_avg = attn_avg / attn_avg.sum(dim=-1, keepdim=True).clamp(min=1e-8)

        result = attn_avg if result is None else torch.matmul(attn_avg, result)
    return result
