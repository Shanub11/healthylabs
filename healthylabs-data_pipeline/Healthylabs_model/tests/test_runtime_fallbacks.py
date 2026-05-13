from types import SimpleNamespace

from healthylabs_inference.core.config import Settings
from healthylabs_inference.orchestrator.intent_guard import IntentGuard
from healthylabs_inference.orchestrator.reflection import ReflectionEngine
from healthylabs_inference.orchestrator.self_rag_router import SelfRAGRouter
from healthylabs_inference.retrieval.models import RetrievalBundle, RetrievedChunk


class RuntimeFailingLLM:
    def generate_json(self, *args, **kwargs):
        raise RuntimeError("provider unavailable")


def test_intent_guard_falls_back_to_emergency_heuristic_on_runtime_error():
    decision = IntentGuard(RuntimeFailingLLM()).classify("I have chest pain and cannot breathe")

    assert decision.intent == "emergency"
    assert decision.source == "heuristic"


def test_router_falls_back_to_direct_on_runtime_error():
    router = SelfRAGRouter(Settings(), RuntimeFailingLLM())
    request = SimpleNamespace(
        query_text="What is pneumonia?",
        patient_context=None,
        model_dump=lambda mode="json": {"query_text": "What is pneumonia?"},
    )

    decision = router.route(request)

    assert decision.strategy == "direct"
    assert decision.source == "parser_fallback"


def test_reflection_falls_back_on_runtime_error():
    decision = ReflectionEngine(RuntimeFailingLLM()).assess(
        query_text="What is pneumonia?",
        strategy="direct",
        bundle=RetrievalBundle(
            chunks=[
                RetrievedChunk(
                    chunk_id="low",
                    text="low confidence evidence",
                    context_id=None,
                    context_text=None,
                    context_metadata={},
                    doc_uid="doc",
                    document_id="doc",
                    vector_score=0.1,
                    authority_score=0.1,
                    tier=3,
                    query_text="query",
                    strategy="direct",
                )
            ]
        ),
        threshold=0.85,
    )

    assert decision.sufficient is False
    assert "parser fallback" in decision.reason.lower()
