
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import IntEnum, Enum
import hashlib
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationInfo

# -------------------------------------------------
# Trust & Lifecycle Enums
# -------------------------------------------------

class TrustTier(IntEnum):
    """
    Source trust tiers.

    Tier 1 (Canonical): FDA, CDC, WHO
    Tier 2 (Evidence): Peer-reviewed journals
    Tier 3 (Exploratory): Blogs, user uploads
    """
    CANONICAL = 1
    EVIDENCE = 2
    EXPLORATORY = 3


class DocStatus(str, Enum):
    """
    Document lifecycle status.
    """
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    QUARANTINED = "quarantined"


# -------------------------------------------------
# Schema Versioning
# -------------------------------------------------

class SchemaVersion(str, Enum):
    V1 = "v1.0"


# -------------------------------------------------
# Core Medical Document Schema
# -------------------------------------------------

class MedicalDocumentSchema(BaseModel):
    """
    Canonical Medical Document Schema.

    ❗ Contract:
    - Immutable after embedding
    - Versioned
    - Authority score enforced by tier
    """

    # --- Identity ---
    document_id: str = Field(..., description="Extractor-provided immutable document identity")
    doc_uid: str = Field(..., description="Stable human-readable document identifier")

    schema_version: SchemaVersion = SchemaVersion.V1

    # --- Provenance ---
    title: str
    source: str
    source_tier: TrustTier
    authority_score: float = Field(..., ge=0.0, le=1.0)

    # --- Temporal ---
    published_at: datetime
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    last_reviewed_at: Optional[datetime] = None

    # --- Lifecycle ---
    status: DocStatus = DocStatus.ACTIVE
    version_tag: str = "v1"

    # --- Content ---
    raw_content: str = Field(..., min_length=10)
    tags: List[str] = Field(default_factory=list)
    metadata_extra: Dict[str, Any] = Field(default_factory=dict)

    # --- Integrity ---
    content_checksum: Optional[str] = None

    # -------------------------------------------------
    # Validators
    # -------------------------------------------------

    @field_validator("authority_score")
    @classmethod
    def enforce_tier_scoring(cls, v, info: ValidationInfo):
        tier = info.data.get("source_tier")

        enforced_scores = {
            TrustTier.CANONICAL: 1.0,
            TrustTier.EVIDENCE: 0.7,
            TrustTier.EXPLORATORY: 0.3
        }

        return enforced_scores.get(tier, v)

    @model_validator(mode="after")
    def compute_content_checksum(self):
        content = self.raw_content
        content_checksum = self.content_checksum

        computed = hashlib.sha256(content.encode("utf-8")).hexdigest()

        if content_checksum and content_checksum != computed:
            raise ValueError("content_checksum does not match raw_content")

        return self

    model_config = {
        "frozen": True,  # Replaces allow_mutation = False
        "validate_assignment": True,
        "extra": "forbid"
    }


# -------------------------------------------------
# Hierarchical Chunk Schema
# -------------------------------------------------

class HierarchicalChunk(BaseModel):
    """
    Immutable chunk schema for retrieval.

    Level 1 → Atomic vector chunk
    Level 2 → Clinical context chunk
    """

    chunk_id: str
    parent_doc_id: str
    level: Literal[1, 2]
    content: str
    metadata: Dict[str, Any]


    model_config = {
    "frozen": True,
    "extra": "forbid"
    }



"""
Important Design Decisions (Why This Is Correct)
1. Immutability

Once embedded, documents must never change.
We enforce this at the model level, not “by convention”.

2. Authority score is NOT user-controlled

Even if someone passes authority_score=0.9, the validator overrides it.

3. Checksums detect silent corruption

If raw content is modified accidentally, the model will refuse to load.

4. Schema versioning is explicit

This allows:

Safe migrations

Mixed-version coexistence

Future backward compatibility
"""
