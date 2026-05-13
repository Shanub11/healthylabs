# HealthyLabs Inference Layer

This package exposes a modular retrieval/model layer for the HealthyLabs RAG medical chatbot. It is designed to plug into the existing FastAPI refinery application and adds a `POST /refinery/v1/query` endpoint.

## Runtime contracts

- **Embeddings:** BioLORD-compatible 768-dimensional vectors.
- **Neo4j vector index:** `atomic_chunk_embeddings` over `AtomicChunk.embedding` with cosine similarity.
- **Neo4j traversal:** `AtomicChunk -> ClinicalContext -> Document`.
- **PostgreSQL metadata:** document citation lookup by `doc_uid` in `medical_metadata`.
- **LLM provider:** Hugging Face MedGemma by default (`google/medgemma-1.5-4b-it` via `HF_TOKEN`), with Gemini still available by setting `LLM_PROVIDER=gemini`.
- **Session memory:** stateless hybrid memory; the backend compresses context and the frontend stores/resends the returned memory fields.
- **Visual assets:** CLIP text search over `MedicalAsset.embedding`, Gemini multimodal synthesis, and presigned MinIO URLs returned to the frontend.

## Minimal integration

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI

from healthylabs_inference.api.routes import SERVICE_STATE_KEY, router as query_router
from healthylabs_inference.service import QueryService

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    service = QueryService.from_settings()
    await asyncio.to_thread(service.direct_strategy.retriever.embedder.embed_query, "warmup")
    setattr(app.state, SERVICE_STATE_KEY, service)
    try:
        yield
    finally:
        service.close()

app = FastAPI(lifespan=lifespan)
app.include_router(query_router)
```

## Visual asset prerequisite

Create the dedicated 512-dimensional CLIP visual index once in Neo4j:

```cypher
CREATE VECTOR INDEX medical_asset_embeddings IF NOT EXISTS
FOR (m:MedicalAsset)
ON m.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 512,
    `vector.similarity_function`: 'cosine'
  }
}
```

## Request memory contract

For long conversations, the frontend should send the latest memory returned by the previous response:

```json
{
  "query_text": "What about the other one?",
  "session_id": "uuid-1234",
  "chat_history": [{"role": "user", "content": "recent turn only if desired"}],
  "session_summary": "Compressed prior conversation.",
  "pinned_medical_facts": {
    "conditions": ["pneumonia"],
    "medications": ["unknown antibiotic"],
    "allergies": []
  },
  "open_questions": ["Which antibiotic is being taken?"],
  "safety_notes": ["Seek care for severe or worsening symptoms."]
}
```

The response includes `updated_session_summary`, `updated_pinned_medical_facts`, `updated_open_questions`, and `updated_safety_notes`. The frontend should persist those values for the next request with the same `session_id`.

## Required environment variables

```bash
export HF_TOKEN="..."
export HF_MODEL_NAME="google/medgemma-1.5-4b-it"
export DATABASE_URL="postgresql+psycopg2://healthylabs_admin:HealthyLabsSecure123@localhost:5432/healthylabs_metadata"
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="HealthyLabsSecure123"
export MINIO_ENDPOINT="localhost:9000"
export MINIO_ACCESS_KEY="..."
export MINIO_SECRET_KEY="..."
```

Optional variables include `LLM_PROVIDER` (`huggingface`, `medgemma`, or `gemini`), `HF_DEVICE_MAP`, `HF_TORCH_DTYPE`, `BIOLORD_MODEL_NAME`, `GEMINI_API_KEY`, `GEMINI_MODEL` (defaults to `gemini-2.5-flash-lite` when Gemini is selected), `RAG_TOP_K`, `RAG_MAX_POOL_SIZE` (defaults to 7 focused chunks), `RAG_INDEX_DOMAINS` (defaults to all domains), `POSTGRES_METADATA_TABLE` (defaults to `medical_metadata`), `RAG_CONFIDENCE_THRESHOLD`, `RAG_MAX_REFLECTION_LOOPS`, `RAG_CHAT_HISTORY_WINDOW` (defaults to 5 recent turns in synthesis), `RAG_MEMORY_RECENT_TURN_WINDOW` (defaults to 8 turns for memory compression), and `RAG_MEMORY_SUMMARY_MAX_WORDS` (defaults to 180), `NEO4J_VISUAL_INDEX` (defaults to `medical_asset_embeddings`), `RAG_VISUAL_SCORE_THRESHOLD` (defaults to 0.60), and MinIO settings (`MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_SECURE`). Leave `RAG_INDEX_DOMAINS` empty to search every Neo4j `AtomicChunk` domain, or set a comma-separated list to restrict retrieval.
