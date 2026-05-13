"""Neo4j vector retrieval facade."""

from __future__ import annotations

from dataclasses import dataclass

from healthylabs_inference.core.database_clients import Neo4jSearchClient
from healthylabs_inference.core.embeddings import BioLORDEmbedder
from healthylabs_inference.retrieval.models import RetrievedChunk


@dataclass(slots=True)
class Neo4jVectorRetriever:
    embedder: BioLORDEmbedder
    search_client: Neo4jSearchClient

    def search(self, query_text: str, *, strategy: str, top_k: int | None = None) -> list[RetrievedChunk]:
        embedding = self.embedder.embed_query(query_text)
        return self.search_client.vector_search(
            query_embedding=embedding,
            query_text=query_text,
            strategy=strategy,
            top_k=top_k,
        )
