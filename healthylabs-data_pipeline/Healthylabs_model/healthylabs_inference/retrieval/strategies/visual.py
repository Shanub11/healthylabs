"""Visual asset retrieval using CLIP text embeddings, Neo4j, and MinIO."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("HealthyLabs.VisualRetrieval")


@dataclass(slots=True)
class VisualResult:
    storage_path: str
    caption: str
    doc_uid: str | None
    score: float
    image_bytes: bytes | None = None
    presigned_url: str | None = None


class VisualRetrievalStrategy:
    def __init__(self, clip_embedder: Any, neo4j_client: Any, minio_client: Any, settings: Any):
        self.embedder = clip_embedder
        self.neo4j_client = neo4j_client
        self.minio_client = minio_client
        self.settings = settings

    def run(self, query_text: str) -> list[VisualResult]:
        vector = self.embedder.embed_text(query_text)
        cypher = """
        CALL db.index.vector.queryNodes($index_name, 3, $vector)
        YIELD node AS m, score
        // 🚨 ADDED: Enforce domain isolation on visual assets
        WHERE score >= $threshold AND ($index_domains = [] OR coalesce(m.index_domain, "") IN $index_domains)
        RETURN
            m.storage_path AS storage_path,
            coalesce(m.caption, '') AS caption,
            m.doc_uid AS doc_uid,
            score
        ORDER BY score DESC
        """
        results: list[VisualResult] = []
        with self.neo4j_client._get_driver().session(database=None) as session:
            records = session.run(
                cypher,
                index_name=self.settings.visual_asset_index_name,
                vector=vector,
                threshold=self.settings.visual_score_threshold,
                # 🚨 ADDED: Pass the settings array to the Cypher query
                index_domains=self.settings.allowed_index_domains,
            )
            for record in records:
                results.append(
                    VisualResult(
                        storage_path=record["storage_path"] or "",
                        caption=record["caption"] or "",
                        doc_uid=record["doc_uid"],
                        score=float(record["score"]),
                    )
                )

        for result in results:
            if not result.storage_path:
                continue
            try:
                result.image_bytes = self.minio_client.get_image_bytes(result.storage_path)
                result.presigned_url = self.minio_client.generate_presigned_url(result.storage_path)
            except Exception as exc:
                logger.warning("MinIO fetch failed for %s: %s", result.storage_path, exc)

        return [result for result in results if result.image_bytes is not None]
