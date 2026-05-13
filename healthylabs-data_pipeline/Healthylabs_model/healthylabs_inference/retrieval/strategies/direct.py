"""Direct retrieval strategy."""

from __future__ import annotations

from dataclasses import dataclass

from healthylabs_inference.retrieval.models import RetrievalBundle
from healthylabs_inference.retrieval.neo4j_search import Neo4jVectorRetriever


@dataclass(slots=True)
class DirectRetrievalStrategy:
    retriever: Neo4jVectorRetriever

    def run(self, query_text: str) -> RetrievalBundle:
        chunks = self.retriever.search(query_text, strategy="direct")
        return RetrievalBundle(
            chunks=chunks,
            trace=[{"strategy": "direct", "query": query_text, "chunks_returned": len(chunks)}],
        )
