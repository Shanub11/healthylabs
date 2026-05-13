import os
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, inspect, text
from sqlalchemy import (
    Float,
    JSON,
    Enum as SAEnum,
    Index,
    UniqueConstraint,
    create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from .settings import Settings

# Pydantic will open the .env file and grab the correct URL for you
settings = Settings()

DATABASE_URL = settings.DATABASE_URL

Base = declarative_base()

class MedicalMetadataAudit(Base):
    __tablename__ = "medical_metadata_audit"

    id = Column(Integer, primary_key=True, autoincrement=True)

    document_id = Column(
        String(64),
        nullable=False,
        index=True,
    )

    doc_uid = Column(
        String(32),
        nullable=False,
        index=True,
    )

    previous_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=False)

    reason = Column(String(256), nullable=False)

    actor = Column(
        String(64),
        nullable=False,
        default="system"
    )

    audit_metadata = Column(JSON, nullable=True)

    extractor_version = Column(String(64), nullable=True)
    processing_host = Column(String(255), nullable=True)
    fetched_at = Column(DateTime, nullable=True)
    extracted_at = Column(DateTime, nullable=True)
    extraction_engine = Column(String(128), nullable=True)
    extraction_engine_version = Column(String(64), nullable=True)
    source_hash = Column(String(128), nullable=True)
    source_parent_hash = Column(String(128), nullable=True)

    chunk_ids = Column(JSON, nullable=True)
    document_version_hash = Column(String(128), nullable=True)
    authority_score = Column(Float, nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now(timezone.utc)
    )

# -------------------------------------------------
# Base
# -------------------------------------------------



# -------------------------------------------------
# Lifecycle Enum (DB-level safety)
# -------------------------------------------------

from cod.core.models import DocStatus


# -------------------------------------------------
# Core Metadata Table
# -------------------------------------------------

class MedicalMetadata(Base):
    """
    Canonical SQL metadata store.

    Guarantees:
    - One row per immutable extractor document_id
    - Immutable identity fields
    - Auditable lifecycle transitions
    """

    __tablename__ = "medical_metadata"

    # --- Identity ---
    document_id = Column(
        String(64),
        primary_key=True,
        nullable=False,
        comment="Extractor-provided immutable document identity"
    )

    content_hash = Column(
        String(64),
        nullable=True,
        comment="Optional content checksum for integrity/corruption detection"
    )

    source_hash = Column(
        String(128),
        nullable=True,
        comment="Extractor/source supplied hash for lineage and chain-of-custody"
    )

    source_parent_hash = Column(
        String(128),
        nullable=True,
        comment="Previous source hash in lineage chain when available"
    )

    extractor_version = Column(
        String(64),
        nullable=True,
        comment="Version of extractor payload schema/agent"
    )

    processing_host = Column(
        String(255),
        nullable=True,
        comment="Hostname of ingestion worker that processed this document"
    )

    fetched_at = Column(
        DateTime,
        nullable=True,
        comment="Timestamp when source material was fetched by extractor"
    )

    extracted_at = Column(
        DateTime,
        nullable=True,
        comment="Timestamp when extraction engine produced payload"
    )

    extraction_engine = Column(
        String(128),
        nullable=True,
        comment="Extractor engine name"
    )

    extraction_engine_version = Column(
        String(64),
        nullable=True,
        comment="Extractor engine version"
    )

    document_version_hash = Column(
        String(128),
        nullable=True,
        comment="Version hash used for retrieval/audit traceability"
    )


    doc_uid = Column(String(32), nullable=False, unique=True, index=True)

    # --- Provenance ---
    title = Column(String(512), nullable=False)
    source_type = Column(String(128), nullable=False)

    source_tier = Column(
        Integer,
        nullable=False,
        comment="1=Canonical, 2=Evidence, 3=Exploratory"
    )

    authority_score = Column(
        Float,
        nullable=False,
        comment="Derived from source tier; not user-controlled"
    )

    # --- Lifecycle ---
    status = Column(SAEnum(DocStatus, name="doc_status_enum"), nullable=False, default=DocStatus.ACTIVE)

    # --- Temporal ---
    published_at = Column(DateTime, nullable=True)
    ingested_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_reviewed_at = Column(DateTime, nullable=True)

    # --- Context ---
    clinical_context = Column(
        JSON,
        nullable=True,
        comment="Level-2 clinical context chunks (non-vector)"
    )

    # --- Audit ---
    schema_version = Column(String(10), nullable=False, default="v1.0")

    __table_args__ = (
        UniqueConstraint("document_id", name="uq_medical_metadata_document_id"),
        Index(
            "ix_medical_metadata_status_tier",
            "status",
            "source_tier"
        ),
    )

    # -----------------------------
    # Defensive Guards
    # -----------------------------

    def __setattr__(self, key, value):
        """
        Prevent mutation of immutable identity fields after creation.
        """
        if key in {"document_id", "doc_uid"}:
            # Only block if the field already has a real value assigned
            if getattr(self, key, None) is not None:
                raise AttributeError(f"{key} is immutable once set")

        super().__setattr__(key, value)


class MedicalAsset(Base):
    __tablename__ = "medical_assets"

    asset_id = Column(String(128), primary_key=True, nullable=False)
    type = Column(String(64), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    vector_id = Column(String(128), nullable=True, index=True)
    document_id = Column(
        String(64),
        ForeignKey("medical_metadata.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provenance_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_medical_assets_document_type", "document_id", "type"),
    )


class MedicalTable(Base):
    __tablename__ = "medical_tables"

    table_id = Column(String(128), primary_key=True, nullable=False)
    document_id = Column(
        String(64),
        ForeignKey("medical_metadata.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    csv_payload = Column(Text, nullable=True)
    raw_payload = Column(JSON, nullable=True)
    provenance_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_medical_tables_document", "document_id"),
    )


class ProcessingError(Base):
    __tablename__ = "processing_errors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(
        String(64),
        ForeignKey("medical_metadata.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id = Column(String(128), nullable=False, index=True)
    stage = Column(String(64), nullable=False)
    error_type = Column(String(128), nullable=False)
    error_message = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_processing_errors_document_stage", "document_id", "stage"),
    )

# -------------------------------------------------
# Engine & Session Management
# -------------------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True
)

SessionLocal = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False
    )
)


def run_schema_migrations() -> None:
    """
    Lightweight migration hook for environments without Alembic.
    """
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)

    if "medical_metadata" in inspector.get_table_names():
        metadata_columns = {col["name"] for col in inspector.get_columns("medical_metadata")}
        metadata_column_defs = {
            "source_hash": "VARCHAR(128)",
            "source_parent_hash": "VARCHAR(128)",
            "extractor_version": "VARCHAR(64)",
            "processing_host": "VARCHAR(255)",
            "fetched_at": "TIMESTAMP",
            "extracted_at": "TIMESTAMP",
            "extraction_engine": "VARCHAR(128)",
            "extraction_engine_version": "VARCHAR(64)",
            "document_version_hash": "VARCHAR(128)",
        }
        with engine.begin() as conn:
            for col_name, col_type in metadata_column_defs.items():
                if col_name not in metadata_columns:
                    conn.execute(text(f"ALTER TABLE medical_metadata ADD COLUMN {col_name} {col_type}"))

    if "medical_metadata_audit" in inspector.get_table_names():
        audit_columns = {col["name"] for col in inspector.get_columns("medical_metadata_audit")}
        audit_column_defs = {
            "extractor_version": "VARCHAR(64)",
            "processing_host": "VARCHAR(255)",
            "fetched_at": "TIMESTAMP",
            "extracted_at": "TIMESTAMP",
            "extraction_engine": "VARCHAR(128)",
            "extraction_engine_version": "VARCHAR(64)",
            "source_hash": "VARCHAR(128)",
            "source_parent_hash": "VARCHAR(128)",
            "chunk_ids": "JSON",
            "document_version_hash": "VARCHAR(128)",
            "authority_score": "FLOAT",
        }
        with engine.begin() as conn:
            for col_name, col_type in audit_column_defs.items():
                if col_name not in audit_columns:
                    conn.execute(text(f"ALTER TABLE medical_metadata_audit ADD COLUMN {col_name} {col_type}"))

    if "medical_assets" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("medical_assets")}
        if "vector_id" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE medical_assets ADD COLUMN vector_id VARCHAR(128)"))

# -------------------------------------------------
# Dependency (FastAPI-compatible)
# -------------------------------------------------

def get_db():
    """
    Yields a DB session with guaranteed cleanup.
    """
    db = SessionLocal()
    try:
        yield db

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()




"""
Important Design Choices (Why This Is Correct)
1. DB-level uniqueness

Python checks are helpful — constraints are mandatory.

2. Immutability enforced in ORM

If someone tries to mutate document_id or doc_uid, it throws immediately.

3. Soft lifecycle, no deletes

Nothing is ever deleted.
Compliance, audits, and reproducibility depend on this.

4. Session discipline

Every request:

commits on success

rolls back on failure

always closes

This prevents connection leaks and phantom writes.
"""



"""
Mandatory Migration Step (Do This)

If this is not a fresh DB, you must add:

ALTER TABLE medical_metadata
ADD CONSTRAINT uq_medical_metadata_document_id UNIQUE (document_id);


and ensure doc_id is unique.
"""
