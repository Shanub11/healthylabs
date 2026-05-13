"""Query decomposition retrieval strategy."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from healthylabs_inference.retrieval.models import RetrievalBundle
from healthylabs_inference.retrieval.neo4j_search import Neo4jVectorRetriever


@dataclass(slots=True)
class DecompositionRetrievalStrategy:
    retriever: Neo4jVectorRetriever

    def run(self, query_text: str, sub_queries: list[str]) -> RetrievalBundle:
        queries = _queries(query_text, sub_queries)
        chunks = []
        trace = []
        for index, query in enumerate(queries, start=1):
            result = self.retriever.search(query, strategy="decompose")
            chunks.extend(result)
            trace.append(
                {
                    "strategy": "decompose",
                    "step": index,
                    "query": query,
                    "chunks_returned": len(result),
                    "concurrent": False,
                }
            )
        return RetrievalBundle(chunks=chunks, trace=trace)

    async def arun(self, query_text: str, sub_queries: list[str]) -> RetrievalBundle:
        queries = _queries(query_text, sub_queries)
        results = await asyncio.gather(
            *(asyncio.to_thread(self.retriever.search, query, strategy="decompose") for query in queries)
        )
        chunks = [chunk for result in results for chunk in result]
        trace = [
            {
                "strategy": "decompose",
                "step": index,
                "query": query,
                "chunks_returned": len(result),
                "concurrent": True,
            }
            for index, (query, result) in enumerate(zip(queries, results, strict=True), start=1)
        ]
        return RetrievalBundle(chunks=chunks, trace=trace)


def _queries(query_text: str, sub_queries: list[str]) -> list[str]:
    return (sub_queries or [
        query_text,
        f"symptom causes and red flags related to: {query_text}",
        f"medication adverse effects and interactions related to: {query_text}",
    ])[:5]
