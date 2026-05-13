import pytest

pytest.importorskip("pydantic")

from healthylabs_inference.api.request_models import Citation
from healthylabs_inference.retrieval.models import RetrievedChunk
from healthylabs_inference.synthesis.response_builder import _build_evidence


def chunk(chunk_id: str, doc_uid: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=f"evidence text {chunk_id}",
        context_id="ctx",
        context_text="clinical context",
        context_metadata={},
        doc_uid=doc_uid,
        document_id=doc_uid,
        vector_score=0.9,
        authority_score=1.0,
        tier=1,
        query_text="query",
        strategy="direct",
    )


def test_build_evidence_keeps_all_chunks_even_when_citations_share_document():
    chunks = [chunk("a", "same-doc"), chunk("b", "same-doc"), chunk("c", "same-doc")]
    citations = [Citation(ref_id="[1]", doc_uid="same-doc")]

    evidence = _build_evidence(chunks, citations)

    assert [item["atomic_chunk"] for item in evidence] == [
        "evidence text a",
        "evidence text b",
        "evidence text c",
    ]
    assert {item["ref_id"] for item in evidence} == {"[1]"}


def test_build_evidence_includes_patient_specific_kg_facts_as_override_evidence():
    evidence = _build_evidence(
        [chunk("a", "doc")],
        [Citation(ref_id="[1]", doc_uid="doc")],
        [{"fact_type": "interaction", "severity": "high"}],
    )

    assert evidence[0]["kind"] == "patient_specific_kg_facts"
    assert evidence[0]["authority"] == "knowledge_graph_override"
    assert evidence[0]["facts"] == [{"fact_type": "interaction", "severity": "high"}]
    assert evidence[1]["kind"] == "retrieved_chunk"
