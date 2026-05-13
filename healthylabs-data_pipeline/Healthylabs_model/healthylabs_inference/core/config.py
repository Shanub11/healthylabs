"""Runtime configuration for the HealthyLabs inference layer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    """Environment-backed settings used by the retrieval/model layer.

    Defaults mirror the local Docker compose values supplied by the HealthyLabs
    pipeline team while allowing production deployments to override everything
    through environment variables.
    """

    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://healthylabs_admin:HealthyLabsSecure123@localhost:5432/healthylabs_metadata",
    )
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "HealthyLabsSecure123")
    llm_provider: str = os.getenv("LLM_PROVIDER", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    hf_token: str = os.getenv("HF_TOKEN", "")
    hf_model_name: str = os.getenv("HF_MODEL_NAME", "google/medgemma-4b-it")
    hf_device_map: str = os.getenv("HF_DEVICE_MAP", "auto")
    hf_torch_dtype: str = os.getenv("HF_TORCH_DTYPE", "auto")
    biolord_model_name: str = os.getenv("BIOLORD_MODEL_NAME", "FremyCompany/BioLORD-2023")
    vector_index_name: str = os.getenv("NEO4J_VECTOR_INDEX", "atomic_chunk_embeddings")
    top_k: int = int(os.getenv("RAG_TOP_K", "8"))
    max_pool_size: int = int(os.getenv("RAG_MAX_POOL_SIZE", "7"))
    confidence_threshold: float = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.85"))
    max_reflection_loops: int = int(os.getenv("RAG_MAX_REFLECTION_LOOPS", "1"))
    request_timeout_seconds: float = float(os.getenv("RAG_REQUEST_TIMEOUT_SECONDS", "120"))
    metadata_table_name: str = os.getenv("POSTGRES_METADATA_TABLE", "medical_metadata")
    allowed_index_domains: list[str] = field(
        default_factory=lambda: _csv_env("RAG_INDEX_DOMAINS", "")
    )
    synthesis_chat_history_window: int = int(os.getenv("RAG_CHAT_HISTORY_WINDOW", "5"))
    memory_recent_turn_window: int = int(os.getenv("RAG_MEMORY_RECENT_TURN_WINDOW", "8"))
    memory_summary_max_words: int = int(os.getenv("RAG_MEMORY_SUMMARY_MAX_WORDS", "180"))
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    enable_visual_retrieval: bool = os.getenv("RAG_ENABLE_VISUAL_RETRIEVAL", "false").lower() == "true"
    visual_asset_index_name: str = os.getenv("NEO4J_VISUAL_INDEX", "medical_asset_embeddings")
    visual_score_threshold: float = float(os.getenv("RAG_VISUAL_SCORE_THRESHOLD", "0.60"))


def get_settings() -> Settings:
    """Return settings loaded from the current process environment."""

    return Settings()


def _csv_env(name: str, default: str = "") -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]
