"""Self-RAG confidence reflection."""

from __future__ import annotations

from dataclasses import dataclass

from healthylabs_inference.core.llm_client import GeminiClient
from healthylabs_inference.orchestrator.prompts import REFLECTION_PROMPT, object_to_json
from healthylabs_inference.retrieval.models import RetrievalBundle


@dataclass(frozen=True, slots=True)
class ReflectionDecision:
    sufficient: bool
    reason: str
    recommended_strategy: str = "direct"


class ReflectionEngine:
    def __init__(self, llm_client: GeminiClient | None = None):
        self._llm = llm_client

    def assess(self, *, query_text: str, strategy: str, bundle: RetrievalBundle, threshold: float) -> ReflectionDecision:
        if bundle.confidence >= threshold:
            return ReflectionDecision(sufficient=True, reason="Composite retrieval confidence met threshold.")
        if self._llm is None or not bundle.chunks:
            return ReflectionDecision(
                sufficient=False,
                reason="Retrieved evidence did not meet the configured confidence threshold.",
                recommended_strategy="multi_query" if strategy == "direct" else "decompose",
            )
        evidence = [
            {
                "text": chunk.text[:500],
                "score": chunk.composite_score,
                "authority": chunk.authority_score,
            }
            for chunk in bundle.chunks[:6]
        ]
        try:
            result = self._llm.generate_json(
                REFLECTION_PROMPT.format(
                    query_text=query_text,
                    strategy=strategy,
                    confidence=round(bundle.confidence, 3),
                    evidence_json=object_to_json(evidence),
                ),
                temperature=0.0,
                max_output_tokens=320,
            )
        except (ValueError, TypeError, RuntimeError):
            return ReflectionDecision(
                sufficient=False,
                reason="Reflection parser fallback; evidence confidence remains below threshold.",
                recommended_strategy="multi_query" if strategy == "direct" else "decompose",
            )
        return ReflectionDecision(
            sufficient=bool(result.get("sufficient", False)),
            reason=str(result.get("reason", "Evidence confidence is below threshold.")),
            recommended_strategy=str(result.get("recommended_strategy", "multi_query")),
        )
