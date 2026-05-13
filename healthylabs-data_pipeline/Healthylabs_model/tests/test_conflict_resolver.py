from healthylabs_inference.retrieval.models import RetrievedChunk
from healthylabs_inference.synthesis.conflict_resolver import ConflictResolver


def test_conflict_resolver_flags_opposing_safety_language():
    chunks = [
        RetrievedChunk(
            chunk_id="1",
            text="This medicine is contraindicated for this population.",
            context_id=None,
            context_text=None,
            context_metadata={},
            doc_uid="doc",
            document_id="docid",
            vector_score=0.8,
            authority_score=1.0,
            tier=1,
            query_text="query",
            strategy="direct",
        ),
        RetrievedChunk(
            chunk_id="2",
            text="Another source says it is safe and recommended.",
            context_id=None,
            context_text=None,
            context_metadata={},
            doc_uid="doc2",
            document_id="docid2",
            vector_score=0.7,
            authority_score=0.7,
            tier=2,
            query_text="query",
            strategy="direct",
        ),
    ]

    report = ConflictResolver().analyze(chunks)

    assert report.contradictions_found is True


def test_conflict_resolver_does_not_flag_single_chunk_mixed_safety_language():
    chunks = [
        RetrievedChunk(
            chunk_id="1",
            text="Aspirin is contraindicated in children, while ibuprofen can be safe for adults.",
            context_id=None,
            context_text=None,
            context_metadata={},
            doc_uid="doc",
            document_id="docid",
            vector_score=0.8,
            authority_score=1.0,
            tier=1,
            query_text="query",
            strategy="direct",
        )
    ]

    report = ConflictResolver().analyze(chunks)

    assert report.contradictions_found is False
