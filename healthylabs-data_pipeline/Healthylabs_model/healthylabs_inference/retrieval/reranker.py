"""Deterministic authority-aware re-ranking and deduplication."""

from __future__ import annotations

from healthylabs_inference.retrieval.models import RetrievedChunk


def dedupe_and_rerank(chunks: list[RetrievedChunk], *, max_items: int) -> list[RetrievedChunk]:
    """Keep the best instance of each chunk and return a focused top-N evidence set.

    Ranking uses the same composite score exposed by ``RetrievedChunk`` so
    reflection, confidence reporting, and evidence selection agree on what a
    high-value medical source means. This keeps decompose/multi-query retrieval
    from flooding synthesis with 15+ chunks and mitigates lost-in-the-middle
    behavior.
    """

    best_by_key: dict[str, RetrievedChunk] = {}
    for chunk in chunks:
        key = chunk.chunk_id or f"{chunk.citation_key}:{chunk.text[:80]}"
        current = best_by_key.get(key)
        if current is None or _rank_score(chunk) > _rank_score(current):
            best_by_key[key] = chunk
    return sorted(best_by_key.values(), key=_rank_score, reverse=True)[:max_items]


def _rank_score(chunk: RetrievedChunk) -> float:
    return chunk.composite_score
