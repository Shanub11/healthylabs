"""Multi-query retrieval strategy."""

from __future__ import annotations

from dataclasses import dataclass

from healthylabs_inference.retrieval.models import RetrievalBundle
from healthylabs_inference.retrieval.neo4j_search import Neo4jVectorRetriever


@dataclass(slots=True)
class MultiQueryRetrievalStrategy:
    retriever: Neo4jVectorRetriever

    def run(self, query_text: str, sub_queries: list[str]) -> RetrievalBundle:
        queries = sub_queries or [query_text]
        chunks = []
        trace = []
        for query in queries[:5]:
            result = self.retriever.search(query, strategy="multi_query")
            chunks.extend(result)
            trace.append({"strategy": "multi_query", "query": query, "chunks_returned": len(result)})
        return RetrievalBundle(chunks=chunks, trace=trace)
