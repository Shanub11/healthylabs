"""Pydantic request and response models for the query endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    """Single chat-history turn supplied by the frontend."""

    role: Literal["system", "user", "assistant"]
    content: str = Field(..., min_length=1, max_length=8_000)


class UploadedImage(BaseModel):
    """User-supplied image attached to a diagnostic chat turn."""

    filename: str | None = Field(default=None, max_length=255)
    content_type: str = Field(default="image/png", max_length=80)
    data_base64: str = Field(..., min_length=1)


class PatientContext(BaseModel):
    """Structured patient context supplied by the frontend.

    The inference layer treats this as user-provided context and never assumes it
    is complete. It is included in prompts so the model can tailor cautious
    educational guidance and in KG queries when patient identifiers are present.
    """

    age: int | None = Field(default=None, ge=0, le=125)
    sex: str | None = None
    pregnancy_status: str | None = None
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    recent_events: list[str] = Field(default_factory=list)
    vitals: dict[str, Any] = Field(default_factory=dict)
    additional_notes: str | None = Field(default=None, max_length=8_000)


class QueryRequest(BaseModel):
    """Incoming natural-language query contract from the website/API caller."""

    query_text: str = Field(..., min_length=2, max_length=6_000)
    session_id: str | None = Field(default=None, max_length=128)
    patient_id: str | None = Field(default=None, max_length=128)
    chat_history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    uploaded_images: list[UploadedImage] = Field(default_factory=list, max_length=3)
    session_summary: str | None = Field(default=None, max_length=8_000)
    pinned_medical_facts: dict[str, Any] = Field(default_factory=dict)
    open_questions: list[str] = Field(default_factory=list, max_length=20)
    safety_notes: list[str] = Field(default_factory=list, max_length=20)
    patient_context: PatientContext | dict[str, Any] | None = None
    request_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("query_text")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        return " ".join(value.strip().split())


class Citation(BaseModel):
    """Auditable source citation returned with the answer."""

    ref_id: str
    title: str | None = None
    source: str | None = None
    doc_uid: str | None = None
    document_id: str | None = None
    source_tier: int | None = None
    authority_score: float | None = None
    snippet: str | None = None


class VisualAsset(BaseModel):
    """Frontend-renderable visual evidence returned from MinIO."""

    url: str
    alt_text: str
    source_document: str | None = None


class QueryResponse(BaseModel):
    """Response contract emitted by `/refinery/v1/query`."""

    answer: str
    strategy_used: Literal["direct", "hyde", "multi_query", "decompose", "emergency"]
    contradictions_found: bool = False
    citations: list[Citation] = Field(default_factory=list)
    visual_assets: list[VisualAsset] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    safety_flags: list[str] = Field(default_factory=list)
    escalation_required: bool = False
    retrieval_trace: list[dict[str, Any]] = Field(default_factory=list)
    updated_session_summary: str | None = None
    updated_pinned_medical_facts: dict[str, Any] = Field(default_factory=dict)
    updated_open_questions: list[str] = Field(default_factory=list)
    updated_safety_notes: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
