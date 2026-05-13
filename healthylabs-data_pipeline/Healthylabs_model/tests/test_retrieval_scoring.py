from healthylabs_inference.retrieval.models import RetrievedChunk
from healthylabs_inference.retrieval.reranker import dedupe_and_rerank


def chunk(chunk_id: str, vector_score: float, authority_score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        text="sample medical text",
        context_id="ctx",
        context_text="broader clinical context",
        context_metadata={},
        doc_uid="doc-1",
        document_id="document-1",
        vector_score=vector_score,
        authority_score=authority_score,
        tier=1,
        query_text="query",
        strategy="direct",
    )


def test_composite_score_balances_vector_and_authority():
    item = chunk("a", 0.9, 1.0)
    assert round(item.composite_score, 3) == 0.928


def test_dedupe_and_rerank_keeps_best_duplicate():
    lower = chunk("same", 0.5, 0.3)
    higher = chunk("same", 0.9, 1.0)
    other = chunk("other", 0.7, 0.7)

    ranked = dedupe_and_rerank([lower, other, higher], max_items=5)

    assert [item.chunk_id for item in ranked] == ["same", "other"]
    assert ranked[0].vector_score == 0.9


def test_reranker_truncates_to_focused_authoritative_context_window():
    ranked = dedupe_and_rerank(
        [
            chunk("low-authority-high-vector", 0.99, 0.3),
            chunk("canonical", 0.82, 1.0),
            chunk("evidence", 0.8, 0.7),
        ],
        max_items=2,
    )

    assert [item.chunk_id for item in ranked] == ["canonical", "low-authority-high-vector"]
