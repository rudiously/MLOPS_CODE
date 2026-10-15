"""
Token-level attribution via Integrated Gradients (Captum), the primary
explainability method. Given a code snippet and the model's vulnerability
prediction, returns per-token attribution scores and aggregates them to
per-line scores so a PR comment can point at specific lines.
"""
from __future__ import annotations

from dataclasses import dataclass

import torch
from captum.attr import IntegratedGradients


@dataclass
class LineAttribution:
    line_number: int
    score: float
    snippet: str


def _embedding_forward_fn(model, attention_mask):
    def fwd(embeds):
        out = model.encoder(inputs_embeds=embeds, attention_mask=attention_mask)
        pooled = out.last_hidden_state[:, 0, :]
        return model.vuln_head(pooled)
    return fwd


def compute_token_attributions(
    model,
    tokenizer,
    code: str,
    device: torch.device,
    target_class: int = 1,
    n_steps: int = 32,
    max_length: int = 512,
) -> list[tuple[str, float]]:
    """Returns (token, attribution_score) pairs for the given code snippet,
    attributing the model's prediction for `target_class` (default: the
    'vulnerable' class) back to input embeddings via Integrated Gradients."""
    model.eval()
    enc = tokenizer(code, truncation=True, max_length=max_length, padding="max_length", return_tensors="pt")
    input_ids = enc["input_ids"].to(device)
    attention_mask = enc["attention_mask"].to(device)

    embedding_layer = model.encoder.get_input_embeddings()
    input_embeds = embedding_layer(input_ids)
    baseline_embeds = torch.zeros_like(input_embeds)

    ig = IntegratedGradients(_embedding_forward_fn(model, attention_mask))
    attributions = ig.attribute(
        input_embeds,
        baselines=baseline_embeds,
        target=target_class,
        n_steps=n_steps,
    )
    # sum attribution across the embedding dimension -> one score per token
    token_scores = attributions.sum(dim=-1).squeeze(0).detach().cpu()

    tokens = tokenizer.convert_ids_to_tokens(input_ids.squeeze(0).cpu().tolist())
    mask = attention_mask.squeeze(0).cpu().tolist()

    results = [
        (tok, float(score))
        for tok, score, m in zip(tokens, token_scores.tolist(), mask)
        if m == 1
    ]
    return results


def aggregate_to_lines(
    code: str,
    token_attributions: list[tuple[str, float]],
    tokenizer,
) -> list[LineAttribution]:
    """Aggregates token-level attributions into per-line scores by
    re-tokenizing the code line-by-line and summing the attribution mass
    that falls on each line's tokens (approximate but effective enough for
    PR-comment purposes)."""
    lines = code.split("\n")
    # Build a rough token->line map by re-encoding each line separately and
    # walking through tokens in order; approximate for subword edge cases.
    line_scores = [0.0] * len(lines)
    token_iter = iter(token_attributions)
    consumed = list(token_attributions)
    cursor = 0

    for line_idx, line in enumerate(lines):
        if not line.strip():
            continue
        line_tokens = tokenizer.tokenize(line)
        n = len(line_tokens)
        chunk = consumed[cursor:cursor + n]
        line_scores[line_idx] = sum(score for _, score in chunk)
        cursor += n

    return [
        LineAttribution(line_number=i + 1, score=score, snippet=lines[i].strip())
        for i, score in enumerate(line_scores)
        if lines[i].strip()
    ]


def top_k_lines(line_attrs: list[LineAttribution], k: int = 5) -> list[LineAttribution]:
    return sorted(line_attrs, key=lambda x: abs(x.score), reverse=True)[:k]
