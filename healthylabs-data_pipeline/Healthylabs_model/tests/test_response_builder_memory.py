import pytest

pytest.importorskip("pydantic")

from healthylabs_inference.api.request_models import ChatMessage, QueryRequest
from healthylabs_inference.core.config import Settings
from healthylabs_inference.synthesis.response_builder import ResponseBuilder


class FailingCitationClient:
    def fetch_citations(self, doc_uids):
        raise AssertionError("citation lookup should not run for empty retrieval results")


class CapturingLLM:
    def __init__(self):
        self.prompt = ""

    def generate(self, prompt, **kwargs):
        self.prompt = prompt
        return type("Response", (), {"text": "answer"})()


def test_empty_chunks_return_before_postgres_citation_lookup():
    builder = ResponseBuilder(CapturingLLM(), FailingCitationClient(), Settings())
    response = builder.build(
        request=QueryRequest(query_text="unknown question"),
        chunks=[],
        contradictions_found=False,
        safety_flags=[],
    )

    assert response.citations == []
    assert "couldn’t find enough trusted" in response.answer


def test_synthesis_prompt_uses_configured_recent_history_window_and_memory():
    llm = CapturingLLM()
    builder = ResponseBuilder(llm, FailingCitationClient(), Settings(synthesis_chat_history_window=2))
    request = QueryRequest(
        query_text="What about that?",
        session_summary="Earlier: user mentioned penicillin allergy.",
        pinned_medical_facts={"allergies": ["penicillin"]},
        open_questions=["Which antibiotic?"],
        safety_notes=["Check allergy before antibiotics."],
        chat_history=[
            ChatMessage(role="user", content="oldest"),
            ChatMessage(role="assistant", content="middle"),
            ChatMessage(role="user", content="newest"),
        ],
    )

    # Empty chunks intentionally avoid citation lookup/LLM synthesis, so call prompt path through a minimal chunk.
    from healthylabs_inference.retrieval.models import RetrievedChunk

    class CitationClient:
        def fetch_citations(self, doc_uids):
            return {"doc": {"doc_uid": "doc", "title": "T", "source": "S"}}

    builder = ResponseBuilder(llm, CitationClient(), Settings(synthesis_chat_history_window=2))
    builder.build(
        request=request,
        chunks=[
            RetrievedChunk(
                chunk_id="c",
                text="clinical evidence",
                context_id=None,
                context_text=None,
                context_metadata={},
                doc_uid="doc",
                document_id="doc",
                vector_score=0.9,
                authority_score=1.0,
                tier=1,
                query_text="q",
                strategy="direct",
            )
        ],
        contradictions_found=False,
        safety_flags=[],
    )

    assert "oldest" not in llm.prompt
    assert "middle" in llm.prompt
    assert "newest" in llm.prompt
    assert "penicillin allergy" in llm.prompt
    assert "Which antibiotic?" in llm.prompt
