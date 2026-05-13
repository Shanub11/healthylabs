from types import SimpleNamespace

from healthylabs_inference.core.config import Settings
from healthylabs_inference.orchestrator.self_rag_router import SelfRAGRouter


class BrokenLLM:
    def generate_json(self, *args, **kwargs):
        raise ValueError("malformed json")


def test_router_falls_back_to_direct_on_malformed_json():
    router = SelfRAGRouter(Settings(), BrokenLLM())
    request = SimpleNamespace(
        query_text="What is pneumonia?",
        patient_context=None,
        model_dump=lambda mode="json": {"query_text": "What is pneumonia?"},
    )

    decision = router.route(request)

    assert decision.strategy == "direct"
    assert decision.source == "parser_fallback"
