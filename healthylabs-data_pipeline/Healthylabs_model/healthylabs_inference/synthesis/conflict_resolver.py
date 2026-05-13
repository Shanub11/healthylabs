"""Lightweight contradiction detection for retrieved medical evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass

from healthylabs_inference.retrieval.models import RetrievedChunk

_CONFLICT_PATTERNS = (
    (re.compile(r"\bcontraindicated\b", re.I), re.compile(r"\bsafe\b|\brecommended\b", re.I)),
    (re.compile(r"\bdo not use\b|\bavoid\b", re.I), re.compile(r"\buse\b|\bcan be used\b", re.I)),
    (re.compile(r"\bno evidence\b", re.I), re.compile(r"\bevidence shows\b|\bproven\b", re.I)),
)
_CONFLICT_NOTE = "Retrieved evidence contains potentially conflicting safety language."


@dataclass(frozen=True, slots=True)
class ConflictReport:
    contradictions_found: bool
    notes: list[str]


class ConflictResolver:
    def analyze(self, chunks: list[RetrievedChunk]) -> ConflictReport:
        texts = [chunk.text for chunk in chunks[:8] if chunk.text]
        notes: set[str] = set()
        for index, text_a in enumerate(texts):
            for text_b in texts[index + 1 :]:
                if _has_pairwise_conflict(text_a, text_b):
                    notes.add(_CONFLICT_NOTE)
        ordered_notes = sorted(notes)
        return ConflictReport(contradictions_found=bool(ordered_notes), notes=ordered_notes)


def _has_pairwise_conflict(text_a: str, text_b: str) -> bool:
    for negative, positive in _CONFLICT_PATTERNS:
        if (negative.search(text_a) and positive.search(text_b)) or (
            positive.search(text_a) and negative.search(text_b)
        ):
            return True
    return False
