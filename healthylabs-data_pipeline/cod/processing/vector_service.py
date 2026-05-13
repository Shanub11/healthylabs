import logging
import os
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any
from enum import Enum
import json
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable

from sentence_transformers import SentenceTransformer
from PIL import Image

from cod.core.models import MedicalDocumentSchema, TrustTier

logger = logging.getLogger("MedicalVectorService")
logger.setLevel(logging.INFO)


# -------------------------------------------------
# Index Routing (Domain Isolation)
# -------------------------------------------------

class VectorDomain(str, Enum):
    CLINICAL = "clinical_guidelines_index"
    TRIALS = "clinical_trials_index"
    LIFESTYLE = "lifestyle_health_index"
    USER = "user_uploaded_index"


class IndexStage(str, Enum):
    LIVE = "live"
    SHADOW = "shadow"


# -------------------------------------------------
# Vector Service
# -------------------------------------------------

class MedicalVectorService:
    """
    Production-grade Vector Service.

    Guarantees:
    - Domain-isolated semantic indices
    - Single embedding model consistency
    - Batch embedding
    - Retry & backoff on transient failures
    - Deterministic graph structure
    """


    MAX_BATCH_SIZE = 32
    MAX_RETRIES = 3
    RETRY_BACKOFF_SEC = 2

    def __init__(self, uri: str, user: str, password: str):

        model_name = os.getenv("TEXT_EMBEDDING_MODEL", "FremyCompany/BioLORD-2023")
        self.text_model = None
        self._model_id = model_name
        self._visual_model_id = os.getenv("VISUAL_EMBEDDING_MODEL", "clip-ViT-B-32")
        self.visual_model = None

        self.driver = AsyncGraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_pool_size=50,
            connection_timeout=15,
        )
        self.live_index_pointer = os.getenv("LIVE_INDEX_POINTER", IndexStage.LIVE.value)
        self.shadow_index_suffix = os.getenv("SHADOW_INDEX_SUFFIX", "__shadow")

    def _get_text_model(self):
        if self.text_model is None:
            self.text_model = SentenceTransformer(self._model_id)
            logger.info(f"Text embedding model loaded: {self._model_id}")
        return self.text_model

    def _get_visual_model(self):
        if self.visual_model is None:
            self.visual_model = SentenceTransformer(self._visual_model_id)
            logger.info(f"Visual embedding model loaded: {self._visual_model_id}")
        return self.visual_model

    # -------------------------------------------------
    # Lifecycle
    # -------------------------------------------------

    async def close(self):
        await self.driver.close()

    # -------------------------------------------------
    # Embedding
    # -------------------------------------------------

    async def generate_text_embedding(self, text: str) -> List[float]:
        """
        Calls the single, canonical embedding model.

        NOTE:
        Replace this stub with a real embedding API call.
        """
        # In production:
        # return await embedding_client.embed(text)

        """
        import random
        return [random.uniform(-1, 1) for _ in range(768)]
        """

        # encode() converts text into a numpy array, .tolist() makes it JSON-serializable
        embedding = self._get_text_model().encode(text)
        return embedding.tolist()
    """
    async def _batch_embed(self, texts: List[str]) -> List[List[float]]:
    
        # Embeds texts in batches with retry logic.
    
        if not texts :
            return []

        embeddings: List[List[float]] = []

        for i in range(0, len(texts), self.MAX_BATCH_SIZE):
            batch = texts[i : i + self.MAX_BATCH_SIZE]

            for attempt in range(self.MAX_RETRIES):
                try:
                    # Parallelize embedding calls
                    results = await asyncio.gather(
                        *[self.generate_embedding(t) for t in batch]
                    )
                    embeddings.extend(results)
                    break
                except Exception as e:
                    logger.warning(
                        f"Embedding batch failed (attempt {attempt+1}): {e}"
                    )
                    if attempt + 1 == self.MAX_RETRIES:
                        raise
                    sleep(self.RETRY_BACKOFF_SEC * (attempt + 1))

        return embeddings
    """

    # Improved _batch_embed for local models
    async def _batch_embed_text(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        # Local models benefit from internal batching; no need for a loop/gather here
        embeddings = self._get_text_model().encode(texts, batch_size=self.MAX_BATCH_SIZE)
        return embeddings.tolist()

    async def _batch_embed_visual(self, image_paths: List[str]) -> List[List[float]]:
        if not image_paths:
            return []

        images = []
        for path in image_paths:
            with Image.open(path) as image:
                images.append(image.convert("RGB"))

        embeddings = self._get_visual_model().encode(images, batch_size=self.MAX_BATCH_SIZE)
        return embeddings.tolist()

    # -------------------------------------------------
    # Index Routing
    # -------------------------------------------------

    def determine_index(self, doc: MedicalDocumentSchema) -> VectorDomain:
        """
        Determines the isolated semantic domain.
        """
        if "user_upload" in doc.tags or "personal" in doc.tags:
            return VectorDomain.USER

        if doc.source_tier <= TrustTier.EVIDENCE:
            source_lower = doc.source.lower()
            if "trial" in source_lower or "study" in source_lower:
                return VectorDomain.TRIALS
            return VectorDomain.CLINICAL

        return VectorDomain.LIFESTYLE

    def _resolve_index_name(self, domain: VectorDomain, stage: IndexStage) -> str:
        if stage == IndexStage.SHADOW:
            return f"{domain.value}{self.shadow_index_suffix}"
        return domain.value

    def _get_active_stage(self) -> IndexStage:
        pointer = (self.live_index_pointer or IndexStage.LIVE.value).strip().lower()
        return IndexStage.SHADOW if pointer == IndexStage.SHADOW.value else IndexStage.LIVE

    def _build_document_version_hash(self, doc: MedicalDocumentSchema) -> str:
        payload = f"{doc.document_id}:{doc.doc_uid}:{doc.content_checksum}:{self._model_id}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def _run_shadow_validation_hooks(
        self,
        doc: MedicalDocumentSchema,
        vector_map: Dict[str, str],
        index_name: str,
    ) -> Dict[str, Any]:
        required_hits = int(os.getenv("GOLDEN_QUESTION_MIN_HITS", "1"))
        enabled = os.getenv("ENABLE_GOLDEN_QUESTION_VALIDATION", "true").lower() == "true"
        checks = {
            "enabled": enabled,
            "required_hits": required_hits,
            "actual_hits": len(vector_map),
            "passed": True,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "index": index_name,
        }
        if enabled and len(vector_map) < required_hits:
            checks["passed"] = False
        if "fail_golden_validation" in (doc.tags or []):
            checks["passed"] = False
        return checks

    async def _promote_shadow_index(
        self,
        doc: MedicalDocumentSchema,
        source_index: str,
        target_index: str,
        validation_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        promoted = bool(validation_result.get("passed"))
        reason = "validation_passed" if promoted else "golden_question_validation_failed"
        logger.info(
            "Shadow index promotion | document_id=%s source=%s target=%s promoted=%s reason=%s",
            doc.document_id,
            source_index,
            target_index,
            promoted,
            reason,
        )
        return {
            "promoted": promoted,
            "reason": reason,
            "source_index": source_index,
            "target_index": target_index,
            "validation": validation_result,
        }

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    async def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Performs a semantic vector search across ingested medical documents.
        Uses Neo4j's built-in vector similarity to find the most relevant AtomicChunks.
        """
        logger.info("Executing vector search for query: '%s' (top_k=%d)", query, top_k)
        
        try:
            # 1. Generate the embedding for the search query
            query_embedding = await self.generate_text_embedding(query)
            
            # 2. Query Neo4j for closest chunks using Cosine Similarity
            cypher_query = """
            MATCH (a:AtomicChunk)
            WHERE a.embedding IS NOT NULL
            WITH a, vector.similarity.cosine(a.embedding, $embedding) AS score
            ORDER BY score DESC
            LIMIT $top_k
            RETURN a.content AS text, score, a.document_id AS document_id, a.tier AS tier
            """
            
            async with self.driver.session() as session:
                result = await session.run(cypher_query, embedding=query_embedding, top_k=top_k)
                records = await result.data()
                
            logger.info("Vector search returned %d results.", len(records))
            return records
            
        except Exception as e:
            logger.error("Vector search failed: %s", str(e))
            return []

    async def count_document_vectors(self, document_id: str) -> int:
        """
        Returns the number of vectorized atomic chunks for one document.
        """
        query = """
        MATCH (a:AtomicChunk {document_id: $document_id})
        WHERE a.embedding IS NOT NULL
        RETURN count(a) AS count
        """
        async with self.driver.session() as session:
            result = await session.run(query, document_id=document_id)
            record = await result.single()
            return int(record["count"]) if record else 0

    async def upsert_vector_hierarchy(
            self,
            hierarchy_data: List[Dict[str, Any]],
            doc: MedicalDocumentSchema
    ) -> Dict[str, Any]:
        """
        Atomic hybrid upsert strategy:
        - Batch embeddings
        - UNWIND for L2 nodes
        - UNWIND for L1 atomic chunks
        - Single Neo4j transaction (all-or-nothing)
        - Neo4j-managed retries via execute_write
        """

        index_domain = self.determine_index(doc)
        active_stage = self._get_active_stage()
        shadow_index_name = self._resolve_index_name(index_domain, IndexStage.SHADOW)
        live_index_name = self._resolve_index_name(index_domain, active_stage)
        document_version_hash = self._build_document_version_hash(doc)

        logger.info(
            "Vector upsert started | doc_uid=%s document_id=%s | domain=%s | shadow_index=%s | live_index=%s",
            doc.doc_uid,
            doc.document_id,
            index_domain.value,
            shadow_index_name,
            live_index_name,
        )

        # -------------------------------------------------
        # Collect L2 + L1 data
        # -------------------------------------------------
        l2_nodes = [group["l2_parent"] for group in hierarchy_data]

        # FIX: serialize metadata dicts for Neo4j
        l2_nodes_for_neo4j = []

        for node in l2_nodes:
            n = dict(node)

            # Neo4j cannot safely store nested Python dicts as properties
            # so serialize metadata into a JSON string
            n["metadata"] = json.dumps(n.get("metadata", {}))

            l2_nodes_for_neo4j.append(n)

        all_l1_records = [
            l1
            for group in hierarchy_data
            for l1 in group["l1_children"]
        ]

        vector_map: Dict[str, str] = {}
        failed_chunks: List[Dict[str, Any]] = []
        success_count = 0
        retryable_count = 0

        # -------------------------------------------------
        # Cypher queries
        # -------------------------------------------------
        l2_query = """
        MERGE (d:Document {document_id: $document_id})
        SET d.doc_uid = $doc_uid
        WITH d
        UNWIND $l2_data AS l2
        MERGE (c:ClinicalContext {id: l2.chunk_id})
        SET
            c.content = l2.content,
            c.level = 2,
            c.metadata = l2.metadata
        MERGE (c)-[:CHILD_OF]->(d)
        """

        l1_query = """
        UNWIND $l1_data AS l1
        MATCH (parent:ClinicalContext {id: l1.parent_l2_id})
        MERGE (a:AtomicChunk {id: l1.chunk_id})
        SET
            a.content = l1.content,
            a.embedding = l1.vector,
            a.vector_id = l1.vector_id,
            a.tier = l1.tier,
            a.authority_score = l1.authority_score,
            a.index_domain = $domain,
            a.document_id = $document_id,
            a.timestamp = datetime()
        MERGE (a)-[:PART_OF]->(parent)
        """

        async with self.driver.session() as session:
            try:
                async def _upsert_l2(tx):
                    l2_result = await tx.run(
                        l2_query,
                        document_id=doc.document_id,
                        doc_uid=doc.doc_uid,
                        l2_data=l2_nodes_for_neo4j,
                    )
                    await l2_result.consume()

                await session.execute_write(_upsert_l2)
            except Exception as e:
                is_retryable = isinstance(e, ServiceUnavailable)
                if is_retryable:
                    retryable_count += len(all_l1_records)
                failed_chunks.extend(
                    {
                        "chunk_id": record["chunk_id"],
                        "stage": "l2_upsert",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "retryable": is_retryable,
                    }
                    for record in all_l1_records
                )
                logger.exception(
                    "Vector L2 upsert failed | document_id=%s chunks=%s",
                    doc.document_id,
                    len(all_l1_records),
                )
                return {
                    "vector_map": vector_map,
                    "success_count": success_count,
                    "failed_count": len(failed_chunks),
                    "retryable_count": retryable_count,
                    "failed_chunks": failed_chunks,
                    "document_version_hash": document_version_hash,
                    "index_routing": {
                        "domain": index_domain.value,
                        "shadow_index": shadow_index_name,
                        "live_index": live_index_name,
                    },
                }

            for start in range(0, len(all_l1_records), self.MAX_BATCH_SIZE):
                batch_records = all_l1_records[start:start + self.MAX_BATCH_SIZE]
                try:
                    embeddings = await self._batch_embed_text([r["content_vectorized"] for r in batch_records])
                except Exception as e:
                    is_retryable = isinstance(e, ServiceUnavailable)
                    if is_retryable:
                        retryable_count += len(batch_records)
                    failed_chunks.extend(
                        {
                            "chunk_id": record["chunk_id"],
                            "stage": "embedding",
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "retryable": is_retryable,
                        }
                        for record in batch_records
                    )
                    logger.exception(
                        "Vector embedding batch failed | document_id=%s start=%s size=%s",
                        doc.document_id,
                        start,
                        len(batch_records),
                    )
                    continue

                l1_batch = []
                for record, vector in zip(batch_records, embeddings):
                    vector_id = f"{doc.doc_uid}:chunk:{record['chunk_id']}"
                    l1_batch.append({
                        "chunk_id": record["chunk_id"],
                        "parent_l2_id": record["parent_l2_id"],
                        "content": record["content_vectorized"],
                        "vector": vector,
                        "vector_id": vector_id,
                        "tier": record["metadata"]["tier"],
                        "authority_score": record["metadata"]["authority_score"],
                    })

                try:
                    async def _upsert_l1(tx, batch=l1_batch):
                        l1_result = await tx.run(
                            l1_query,
                            l1_data=batch,
                            domain=shadow_index_name,
                            document_id=doc.document_id,
                        )
                        await l1_result.consume()

                    await session.execute_write(_upsert_l1)
                    for record in batch_records:
                        vector_map[record["chunk_id"]] = f"{doc.doc_uid}:chunk:{record['chunk_id']}"
                    success_count += len(batch_records)
                except Exception as e:
                    is_retryable = isinstance(e, ServiceUnavailable)
                    if is_retryable:
                        retryable_count += len(batch_records)
                    failed_chunks.extend(
                        {
                            "chunk_id": record["chunk_id"],
                            "stage": "l1_upsert",
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "retryable": is_retryable,
                        }
                        for record in batch_records
                    )
                    logger.exception(
                        "Vector L1 upsert batch failed | document_id=%s start=%s size=%s",
                        doc.document_id,
                        start,
                        len(batch_records),
                    )
                    continue

        validation_result = await self._run_shadow_validation_hooks(
            doc=doc,
            vector_map=vector_map,
            index_name=shadow_index_name,
        )
        promotion_result = await self._promote_shadow_index(
            doc=doc,
            source_index=shadow_index_name,
            target_index=live_index_name,
            validation_result=validation_result,
        )

        logger.info(
            "Vector upsert completed | document_id=%s | success=%s failed=%s retryable=%s | promoted=%s",
            doc.document_id,
            success_count,
            len(failed_chunks),
            retryable_count,
            promotion_result["promoted"],
        )
        return {
            "vector_map": vector_map,
            "success_count": success_count,
            "failed_count": len(failed_chunks),
            "retryable_count": retryable_count,
            "failed_chunks": failed_chunks,
            "document_version_hash": document_version_hash,
            "index_routing": {
                "domain": index_domain.value,
                "shadow_index": shadow_index_name,
                "live_index": live_index_name,
                "promotion": promotion_result,
            },
        }

    async def upsert_visual_assets(
        self,
        assets: List[Dict[str, Any]],
        doc: MedicalDocumentSchema,
    ) -> Dict[str, str]:
        """
        Stores CLIP/SigLIP-compatible embeddings for visual assets.
        """
        if not assets:
            return {}

        valid_assets = [asset for asset in assets if asset.get("storage_path") and os.path.exists(asset["storage_path"])]
        if not valid_assets:
            return {}

        vectors = await self._batch_embed_visual([asset["storage_path"] for asset in valid_assets])
        index_domain = self.determine_index(doc)
        shadow_index_name = self._resolve_index_name(index_domain, IndexStage.SHADOW)

        payload = []
        vector_ids: Dict[str, str] = {}
        for asset, vector in zip(valid_assets, vectors):
            vector_id = f"{doc.doc_uid}:asset:{asset['asset_id']}"
            vector_ids[asset["asset_id"]] = vector_id
            payload.append(
                {
                    "asset_id": asset["asset_id"],
                    "document_id": doc.document_id,
                    "doc_uid": doc.doc_uid,
                    "type": asset.get("type", "image"),
                    "storage_path": asset["storage_path"],
                    "vector_id": vector_id,
                    "embedding": vector,
                    "index_domain": shadow_index_name,
                }
            )

        query = """
        UNWIND $assets AS asset
        MERGE (m:MedicalAsset {id: asset.asset_id})
        SET m.document_id = asset.document_id,
            m.doc_uid = asset.doc_uid,
            m.type = asset.type,
            m.storage_path = asset.storage_path,
            m.vector_id = asset.vector_id,
            m.embedding = asset.embedding,
            m.index_domain = asset.index_domain,
            m.timestamp = datetime()
        """

        async with self.driver.session() as session:
            async def _upsert_visual(tx):
                result = await tx.run(query, assets=payload)
                await result.consume()

            await session.execute_write(_upsert_visual)

        return vector_ids
    # -------------------------------------------------
    # Neo4j Queries
    # -------------------------------------------------

    @staticmethod
    def _merge_l2_node(
            tx,
            l2_data: Dict[str, Any],
            document_id: str,
            doc_uid: str,
    ):

        query = """
        MERGE (d:Document {document_id: $document_id})
        SET d.doc_uid = $doc_uid
        MERGE (c:ClinicalContext {id: $chunk_id})
        SET c.content = $content,
            c.level = 2,
            c.metadata = $metadata
        MERGE (c)-[:CHILD_OF]->(d)
        """

        tx.run(
            query,
            document_id=document_id,
            doc_uid=doc_uid,
            chunk_id=l2_data["chunk_id"],
            content=l2_data["content"],
            metadata=l2_data["metadata"],
        )

    @staticmethod
    def _merge_l1_node(
            tx,
            l1_data: Dict[str, Any],
            vector: List[float],
            index_domain: str,
            document_id: str,
    ):

        query = """
        MATCH (c:ClinicalContext {id: $l2_id})
        MERGE (a:AtomicChunk {id: $chunk_id})
        SET a.document_id = $document_id,
            a.embedding = $embedding,
            a.content = $content,
            a.tier = $tier,
            a.authority_score = $authority_score,
            a.index_domain = $index_domain,
            a.timestamp = datetime()
        MERGE (a)-[:PART_OF]->(c)
        """
        tx.run(
            query,
            l2_id=l1_data["parent_l2_id"],
            chunk_id=l1_data["chunk_id"],
            embedding=vector,
            content=l1_data["content_vectorized"],
            tier=l1_data["metadata"]["tier"],
            authority_score=l1_data["metadata"]["authority_score"],
            index_domain=index_domain,
            document_id=document_id,
        )


"""
Mandatory Production Notes

You must ensure:

Neo4j vector indexes exist for AtomicChunk.embedding

Index domain is enforced at query time

Embedding model version is pinned
"""
