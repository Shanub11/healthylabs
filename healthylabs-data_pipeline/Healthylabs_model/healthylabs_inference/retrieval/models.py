"""Shared retrieval data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: str
    text: str
    context_id: str | None
    context_text: str | None
    context_metadata: dict[str, Any]
    doc_uid: str | None
    document_id: str | None
    vector_score: float
    authority_score: float
    tier: int | None
    query_text: str
    strategy: str
    index_domain: str | None = None

    @property
    def composite_score(self) -> float:
        authority = min(max(self.authority_score, 0.0), 1.0)
        vector = min(max(self.vector_score, 0.0), 1.0)
        return (vector * 0.72) + (authority * 0.28)

    @property
    def citation_key(self) -> str:
        return self.doc_uid or self.document_id or self.chunk_id


@dataclass(slots=True)
class RetrievalBundle:
    chunks: list[RetrievedChunk] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        if not self.chunks:
            return 0.0
        top = self.chunks[: min(5, len(self.chunks))]
        return sum(chunk.composite_score for chunk in top) / len(top)
