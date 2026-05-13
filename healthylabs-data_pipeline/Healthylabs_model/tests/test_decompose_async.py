import asyncio
import time

from healthylabs_inference.retrieval.models import RetrievedChunk
from healthylabs_inference.retrieval.strategies.decompose import DecompositionRetrievalStrategy


class SlowRetriever:
    def search(self, query_text: str, *, strategy: str, top_k=None):
        time.sleep(0.05)
        return [
            RetrievedChunk(
                chunk_id=query_text,
                text=query_text,
                context_id=None,
                context_text=None,
                context_metadata={},
                doc_uid=query_text,
                document_id=query_text,
                vector_score=0.9,
                authority_score=1.0,
                tier=1,
                query_text=query_text,
                strategy=strategy,
            )
        ]


def test_decompose_arun_executes_subqueries_concurrently():
    strategy = DecompositionRetrievalStrategy(SlowRetriever())
    start = time.perf_counter()

    bundle = asyncio.run(strategy.arun("base", ["a", "b", "c"]))

    elapsed = time.perf_counter() - start
    assert len(bundle.chunks) == 3
    assert all(item["concurrent"] for item in bundle.trace)
    assert elapsed < 0.14
