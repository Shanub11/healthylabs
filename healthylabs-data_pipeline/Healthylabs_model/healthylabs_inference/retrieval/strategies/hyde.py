"""HYDE retrieval strategy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from healthylabs_inference.core.llm_client import GeminiClient
from healthylabs_inference.orchestrator.prompts import HYDE_PROMPT, object_to_json
from healthylabs_inference.retrieval.models import RetrievalBundle
from healthylabs_inference.retrieval.neo4j_search import Neo4jVectorRetriever


@dataclass(slots=True)
class HyDERetrievalStrategy:
    retriever: Neo4jVectorRetriever
    llm_client: GeminiClient

    def run(self, query_text: str, patient_context: Any = None) -> RetrievalBundle:
        hypothetical_doc = self.llm_client.generate(
            HYDE_PROMPT.format(
                query_text=query_text,
                patient_context_json=object_to_json(patient_context or {}),
            ),
            temperature=0.2,
            max_output_tokens=360,
        ).text
        chunks = self.retriever.search(hypothetical_doc, strategy="hyde")
        return RetrievalBundle(
            chunks=chunks,
            trace=[
                {
                    "strategy": "hyde",
                    "query": query_text,
                    "hypothetical_doc_preview": hypothetical_doc[:240],
                    "chunks_returned": len(chunks),
                }
            ],
        )
