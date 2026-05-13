from typing import Optional, Dict, Any
from enum import Enum
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import select

from cod.core.errors import InvalidDocumentError
from cod.core.errors import DuplicateDocumentError

from cod.core.database import MedicalMetadata
from cod.services.classifier import SourceClassifier


class IngestionDecision(str, Enum):
    ACCEPTED = "accepted"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    REJECTED_INVALID = "rejected_invalid"


class IntegrityEngine:
    """
    Implements Section 2.2: Data Integrity & Deduplication (Production-Grade).

    Guarantees:
    - Extractor-provided identity only
    - DB-enforced uniqueness
    - Safe under concurrency
    """

    @staticmethod
    def validate_document_id(document_id: str) -> str:
        if not document_id or not document_id.strip():
            raise ValueError("document_id is required for idempotent ingestion")
        return document_id.strip()

    @staticmethod
    def exists(db: Session, document_id: str) -> bool:
        """
        Fast existence check using indexed primary key.
        """
        stmt = select(MedicalMetadata.document_id).where(
            MedicalMetadata.document_id == document_id
        )
        return db.execute(stmt).first() is not None


class IngestionGatekeeper:
    """
    Orchestrates safe ingestion.

    Responsibilities:
    - Deduplication (hard guarantee)
    - Trust classification
    - Idempotent behavior
    """

    def __init__(self, db_session: Session, classifier: Optional[SourceClassifier] = None):
        self.db = db_session
        self.integrity = IntegrityEngine()
        self.classifier = classifier or SourceClassifier()

    async def validate_and_classify(
        self,
        raw_content: str,
        source_hint: str,
        document_id: str,
    ) -> Dict[str, Any]:
        """
        Entry point for ingestion.

        Returns a structured decision object instead of implicit None.
        """

        if not raw_content or not raw_content.strip():
            raise InvalidDocumentError("Cannot ingest empty content")

        try:
            canonical_document_id = self.integrity.validate_document_id(document_id)
        except ValueError as e:
            raise InvalidDocumentError(str(e))

        classification = self.classifier.classify(source_hint)
        doc_uid = f"HL-{uuid.uuid4().hex[:10]}"

        existing_doc = self.db.execute(
            select(MedicalMetadata.doc_uid).where(
                MedicalMetadata.document_id == canonical_document_id
            )
        ).first()

        if existing_doc:
            raise DuplicateDocumentError(existing_doc[0])

        return {
            "decision": IngestionDecision.ACCEPTED,
            "document_id": canonical_document_id,
            "doc_uid": doc_uid,
            "tier": classification.tier,
            "authority_score": classification.authority_score,
            "classification_confidence": classification.confidence,
            "matched_patterns": classification.matched_patterns,
        }
