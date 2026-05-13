"""Read-only database clients for Neo4j vector search and PostgreSQL citations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from healthylabs_inference.core.config import Settings
from healthylabs_inference.retrieval.models import RetrievedChunk


@dataclass(slots=True)
class Neo4jSearchClient:
    settings: Settings
    _driver: Any = field(init=False, default=None)

    def _get_driver(self):
        if self._driver is None:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                self.settings.neo4j_uri,
                auth=(self.settings.neo4j_user, self.settings.neo4j_password),
            )
        return self._driver

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def vector_search(
        self,
        *,
        query_embedding: list[float],
        query_text: str,
        strategy: str,
        top_k: int | None = None,
        index_domains: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        limit = top_k or self.settings.top_k
        domains = self.settings.allowed_index_domains if index_domains is None else index_domains
        cypher = """
        CALL db.index.vector.queryNodes($index_name, $top_k, $query_embedding)
        YIELD node AS a, score
        WHERE ($index_domains = [] OR coalesce(a.index_domain, "") IN $index_domains)
        OPTIONAL MATCH (a)-[:PART_OF]->(c:ClinicalContext)-[:CHILD_OF]->(d:Document)
        RETURN
            coalesce(a.id, elementId(a)) AS chunk_id,
            a.content AS text,
            c.id AS context_id,
            c.content AS context_text,
            c.metadata AS context_metadata,
            d.doc_uid AS doc_uid,
            coalesce(a.document_id, d.document_id) AS document_id,
            score AS vector_score,
            coalesce(a.authority_score, 0.3) AS authority_score,
            a.tier AS tier,
            a.index_domain AS index_domain
        ORDER BY score DESC
        """
        with self._get_driver().session(database=None) as session:
            records = session.run(
                cypher,
                index_name=self.settings.vector_index_name,
                top_k=limit,
                query_embedding=query_embedding,
                index_domains=domains,
            )
            return [
                RetrievedChunk(
                    chunk_id=str(record["chunk_id"]),
                    text=record["text"] or "",
                    context_id=record["context_id"],
                    context_text=record["context_text"],
                    context_metadata=_loads_metadata(record["context_metadata"]),
                    doc_uid=record["doc_uid"],
                    document_id=record["document_id"],
                    vector_score=float(record["vector_score"] or 0.0),
                    authority_score=float(record["authority_score"] or 0.3),
                    tier=int(record["tier"]) if record["tier"] is not None else None,
                    query_text=query_text,
                    strategy=strategy,
                    index_domain=record["index_domain"],
                )
                for record in records
            ]

    def patient_drug_facts(self, *, patient_id: str, drug_names: list[str]) -> list[dict[str, Any]]:
        if not patient_id and not drug_names:
            return []
        normalized = [name.lower() for name in drug_names]
        facts: list[dict[str, Any]] = []
        if patient_id and normalized:
            prescribed_cypher = """
            MATCH (d:Drug)-[r:PRESCRIBED]->(p:Patient {id: $patient_id})
            WHERE toLower(d.name) IN $drug_names
            RETURN 'prescription' AS fact_type, d.name AS drug_name, r.dosage AS dosage,
                   r.frequency AS frequency, r.unit AS unit, r.authority AS authority
            """
            with self._get_driver().session(database=None) as session:
                records = session.run(
                    prescribed_cypher, patient_id=patient_id, drug_names=normalized
                )
                facts.extend(dict(record) for record in records)
        if len(normalized) >= 2:
            interaction_cypher = """
            MATCH (d1:Drug)-[r:INTERACTS_WITH]-(d2:Drug)
            WHERE toLower(d1.name) IN $drug_names AND toLower(d2.name) IN $drug_names
            RETURN DISTINCT 'interaction' AS fact_type, d1.name AS drug_a, d2.name AS drug_b,
                   r.severity AS severity, r.mechanism AS mechanism, r.evidence AS evidence,
                   r.authority AS authority
            """
            with self._get_driver().session(database=None) as session:
                records = session.run(interaction_cypher, drug_names=normalized)
                facts.extend(dict(record) for record in records)
        return facts


@dataclass(slots=True)
class PostgresCitationClient:
    settings: Settings
    _engine: Any = field(init=False, default=None)

    def _get_engine(self):
        if self._engine is None:
            from sqlalchemy import create_engine

            self._engine = create_engine(self.settings.database_url, pool_pre_ping=True)
        return self._engine

    def close(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None

    def fetch_citations(self, doc_uids: list[str]) -> dict[str, dict[str, Any]]:
        if not doc_uids:
            return {}
        from sqlalchemy import text

        table_name = _safe_table_identifier(self.settings.metadata_table_name)
        query = text(
            "SELECT document_id, doc_uid, title, source_type AS source, source_tier, authority_score "
            f"FROM {table_name} WHERE doc_uid = ANY(:doc_uids)"
        )
        with self._get_engine().connect() as connection:
            rows = connection.execute(query, {"doc_uids": doc_uids}).mappings().all()
        return {str(row["doc_uid"]): dict(row) for row in rows}


def _loads_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {"raw": parsed}
    return {}


def _safe_table_identifier(table_name: str) -> str:
    """Return a safely quoted SQL identifier for the configured metadata table."""

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?", table_name):
        raise ValueError(f"Unsafe PostgreSQL metadata table name: {table_name!r}")
    return ".".join(f'"{part}"' for part in table_name.split("."))


class MinioImageClient:
    """MinIO image adapter for visual evidence bytes and presigned URLs."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = None

    def _get_client(self):
        if self._client is None:
            from minio import Minio

            endpoint = self._settings.minio_endpoint.replace("http://", "").replace("https://", "")
            self._client = Minio(
                endpoint,
                access_key=self._settings.minio_access_key,
                secret_key=self._settings.minio_secret_key,
                secure=self._settings.minio_secure,
            )
        return self._client

    def _parse_path(self, storage_path: str) -> tuple[str, str]:
        without_scheme = storage_path.replace("s3://", "", 1)
        bucket, key = without_scheme.split("/", 1)
        return bucket, key

    def get_image_bytes(self, storage_path: str) -> bytes:
        bucket, key = self._parse_path(storage_path)
        response = self._get_client().get_object(bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def generate_presigned_url(self, storage_path: str, expiry_seconds: int = 3600) -> str:
        from datetime import timedelta

        bucket, key = self._parse_path(storage_path)
        return self._get_client().presigned_get_object(
            bucket,
            key,
            expires=timedelta(seconds=expiry_seconds),
        )
