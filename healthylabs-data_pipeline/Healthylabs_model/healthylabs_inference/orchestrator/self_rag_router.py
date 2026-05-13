"""Self-RAG strategy router."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from healthylabs_inference.api.request_models import QueryRequest
from healthylabs_inference.core.config import Settings
from healthylabs_inference.core.llm_client import GeminiClient
from healthylabs_inference.orchestrator.prompts import SELF_RAG_ROUTER_PROMPT, request_to_json

Strategy = Literal["direct", "hyde", "multi_query", "decompose"]


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    strategy: Strategy
    reason: str
    sub_queries: list[str] = field(default_factory=list)
    knowledge_graph_override_required: bool = False
    confidence_threshold: float = 0.85
    source: str = "heuristic"


class SelfRAGRouter:
    def __init__(self, settings: Settings, llm_client: GeminiClient | None = None):
        self._settings = settings
        self._llm = llm_client

    def route(self, request: QueryRequest) -> RoutingDecision:
        heuristic = self._heuristic(request)
        if self._llm is None:
            return heuristic
        prompt = SELF_RAG_ROUTER_PROMPT.format(request_json=request_to_json(request))
        try:
            result = self._llm.generate_json(prompt, temperature=0.0, max_output_tokens=520)
        except (ValueError, TypeError, RuntimeError):
            return RoutingDecision(
                strategy="direct",
                reason="Fallback due to router JSON parser error.",
                confidence_threshold=self._settings.confidence_threshold,
                source="parser_fallback",
            )
        strategy = result.get("strategy", heuristic.strategy)
        if strategy not in {"direct", "hyde", "multi_query", "decompose"}:
            strategy = heuristic.strategy
        sub_queries = [str(item) for item in result.get("sub_queries", []) if str(item).strip()]
        return RoutingDecision(
            strategy=strategy,
            reason=str(result.get("reason", heuristic.reason)),
            sub_queries=sub_queries[:5],
            knowledge_graph_override_required=bool(
                result.get("knowledge_graph_override_required", heuristic.knowledge_graph_override_required)
            ),
            confidence_threshold=float(
                result.get("confidence_threshold", self._settings.confidence_threshold)
            ),
            source="llm",
        )

    def _heuristic(self, request: QueryRequest) -> RoutingDecision:
        query = request.query_text.lower()
        patient_context = request.patient_context
        has_patient_risk_context = bool(patient_context) and any(
            token in str(patient_context).lower()
            for token in ("medication", "allerg", "pregnan", "condition", "dose")
        )
        multi_intent_terms = (" after ", " while ", " with ", "interaction", "side effect", "because")
        vague_terms = ("feel weird", "not feeling well", "what's wrong", "why am i", "symptoms")
        if any(term in query for term in multi_intent_terms) and len(query.split()) > 7:
            return RoutingDecision(
                strategy="decompose",
                reason="The query combines multiple clinical concepts and needs sub-question retrieval.",
                sub_queries=_fallback_subqueries(request.query_text),
                knowledge_graph_override_required=has_patient_risk_context,
                confidence_threshold=self._settings.confidence_threshold,
            )
        if any(term in query for term in vague_terms):
            return RoutingDecision(
                strategy="hyde",
                reason="The query is vague and benefits from semantic expansion before retrieval.",
                knowledge_graph_override_required=has_patient_risk_context,
                confidence_threshold=self._settings.confidence_threshold,
            )
        if "/" in query or " or " in query or " vs " in query:
            return RoutingDecision(
                strategy="multi_query",
                reason="The query has alternate interpretations or comparison language.",
                sub_queries=_fallback_subqueries(request.query_text),
                knowledge_graph_override_required=has_patient_risk_context,
                confidence_threshold=self._settings.confidence_threshold,
            )
        return RoutingDecision(
            strategy="direct",
            reason="The query is specific enough for direct vector retrieval.",
            knowledge_graph_override_required=has_patient_risk_context,
            confidence_threshold=self._settings.confidence_threshold,
        )


def _fallback_subqueries(query_text: str) -> list[str]:
    return [
        query_text,
        f"medical causes and differential considerations for: {query_text}",
        f"medication adverse effects, contraindications, and safety warnings related to: {query_text}",
    ]
