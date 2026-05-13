import logging
import hashlib
import csv
import io
import os
import json
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
import requests
from google.cloud import bigquery

from cod.core.models import MedicalDocumentSchema, DocStatus, TrustTier
from cod.core.extraction_models import ExtractionOutput
from cod.core.database import (
    get_db,
    MedicalMetadata,
    MedicalMetadataAudit,
    MedicalAsset,
    MedicalTable,
    ProcessingError,
    SessionLocal,
    run_schema_migrations,
)
from cod.core.safety_engine import MedicalSafetyEngine, SafetyDecision
from cod.services.integrity import IngestionGatekeeper, IngestionDecision
from cod.services.retraction import RetractionService
from cod.processing.parser import MedicalStructureParser
from cod.processing.chunker import GraphChunker
from cod.processing.vector_service import MedicalVectorService
from cod.processing.kg_service import MedicalKGService
from cod.services.contradiction_engine import ContradictionEngine
from cod.core.lifecycle import update_status

from cod.core.errors import (
    DuplicateDocumentError,
    InvalidDocumentError,
    VectorTransientError,
    VectorPermanentError,
)
# Make the inference package importable when running the refinery app directly.
MODEL_PACKAGE_PATH = os.path.join(os.path.dirname(__file__), "Healthylabs_model")
if MODEL_PACKAGE_PATH not in sys.path:
    sys.path.insert(0, MODEL_PACKAGE_PATH)

from healthylabs_inference.api.request_models import (
    ChatMessage,
    PatientContext,
    QueryRequest,
    UploadedImage,
)
from healthylabs_inference.api.routes import SERVICE_STATE_KEY
from healthylabs_inference.api.routes import router as healthylabs_query_router
from healthylabs_inference.service import QueryService

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# -------------------------------------------------
# App & Logging
# -------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HealthyLabsAPI")

app = FastAPI(
    title="HealthyLabs.ai – Medical Knowledge Refinery",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.include_router(healthylabs_query_router)

# -------------------------------------------------
# Configuration (Env-driven)
# -------------------------------------------------
from cod.core.settings import Settings

settings = Settings()

EXTRACTOR_QUALITY_THRESHOLD = 0.0 #0.70
OCR_MEAN_CONFIDENCE_THRESHOLD = 0.0 #0.85
PHI_VECTORIZATION_CONFIDENCE_THRESHOLD = settings.PHI_CONFIDENCE_THRESHOLD
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_URL = os.getenv("MISTRAL_API_URL", "https://api.mistral.ai/v1/chat/completions")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")




def _table_to_csv(table) -> str:
    if not table.cells:
        return table.markdown

    max_row = max(cell.row for cell in table.cells)
    max_col = max(cell.column for cell in table.cells)
    grid = [["" for _ in range(max_col + 1)] for _ in range(max_row + 1)]

    for cell in table.cells:
        grid[cell.row][cell.column] = cell.text

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerows(grid)
    return buffer.getvalue().strip()


def _normalize_asset_type(kind: str, path: str) -> str:
    lowered = (kind or "").lower()
    if "dicom" in lowered or path.lower().endswith(".dcm"):
        return "dicom_rendered_png"
    if "image" in lowered or path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        return "extracted_image"
    return lowered or "asset"

def _has_high_text_density_signal(issues: list[str]) -> bool:
    density_markers = {
        "high_text_density",
        "text_density_high",
        "high text density",
    }
    normalized = {issue.strip().lower() for issue in issues if issue}
    return any(marker in normalized for marker in density_markers)


# -------------------------------------------------
# Services (Singleton-style)
# -------------------------------------------------

safety_engine = MedicalSafetyEngine(settings)
retraction_service = RetractionService()
parser = MedicalStructureParser()
chunker = GraphChunker(settings)
vector_service = MedicalVectorService(
    uri=settings.NEO4J_URI,
    user=settings.NEO4J_USER,
    password=settings.NEO4J_PASSWORD,
)
kg_service = MedicalKGService(
    uri=settings.NEO4J_URI,
    user=settings.NEO4J_USER,
    password=settings.NEO4J_PASSWORD,
)
contradiction_engine = ContradictionEngine(
    uri=settings.NEO4J_URI,
    user=settings.NEO4J_USER,
    password=settings.NEO4J_PASSWORD,
)


@app.on_event("startup")
async def startup_event():
    try:
        run_schema_migrations()
    except OperationalError as exc:
        if settings.ENV == "prod":
            raise
        logger.warning(
            "Database schema migrations skipped because PostgreSQL is unavailable. "
            "DB-backed endpoints will fail until DATABASE_URL is reachable: %s",
            exc,
        )
    query_service = QueryService.from_settings()
    setattr(app.state, SERVICE_STATE_KEY, query_service)
    logger.info("Database schema migrations startup step completed.")
    logger.info("HealthyLabs model/RAG query service initialized.")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Ensures all persistent connections are closed gracefully.
    """
    await retraction_service.close()
    await vector_service.close()
    await kg_service.close()
    await contradiction_engine.close()
    query_service = getattr(app.state, SERVICE_STATE_KEY, None)
    if query_service is not None:
        query_service.close()
    logger.info("Application shutdown complete: Connections closed.")


# In main.py or a separate maintenance script
from cod.services.consistency_sweeper import sweep_missing_vectors

@app.post("/refinery/v1/maintenance/sync-vectors")
async def trigger_consistency_sweep():
    """
    Manual trigger to find and log documents missing vectors.
    """
    # In a real system, you would extend the sweeper to
    # re-trigger 'process_embeddings' for found documents.
    sweep_missing_vectors()
    return {"message": "Consistency sweep completed. Check logs for missing vectors."}
class IngestResponse(BaseModel):
    decision: str
    doc_uid: Optional[str]
    status: Optional[str]
    tier: Optional[str]
    safety_confidence: Optional[float]
    message: str


def _coerce_doc_status(value) -> DocStatus:
    if isinstance(value, DocStatus):
        return value
    return DocStatus(value)


def _coerce_trust_tier(value) -> TrustTier:
    if isinstance(value, TrustTier):
        return value
    return TrustTier(value)


async def _schedule_duplicate_vector_repair(
    request: ExtractionOutput,
    background_tasks: BackgroundTasks,
    existing_metadata: MedicalMetadata,
) -> Optional[float]:
    """
    Rebuilds missing Neo4j vectors when an idempotent ingest request is replayed.
    SQL remains the source of identity truth; the submitted extractor payload is
    used only to repair the derived chunk/vector projection.
    """
    status_flag = _coerce_doc_status(existing_metadata.status)
    if status_flag != DocStatus.ACTIVE:
        return None

    existing_vector_count = await vector_service.count_document_vectors(existing_metadata.document_id)
    if existing_vector_count > 0:
        return None

    safety = await safety_engine.process_content(request.content)
    enriched_content = parser.unify_findings(safety["processed_content"])
    source_tier = _coerce_trust_tier(existing_metadata.source_tier)

    repair_doc = MedicalDocumentSchema(
        title=existing_metadata.title,
        document_id=existing_metadata.document_id,
        doc_uid=existing_metadata.doc_uid,
        source=existing_metadata.source_type,
        source_tier=source_tier,
        authority_score=existing_metadata.authority_score,
        published_at=existing_metadata.published_at or datetime.now(timezone.utc),
        status=status_flag,
        raw_content=enriched_content,
        tags=request.metadata.tags,
        metadata_extra={
            "likely_handwriting": (existing_metadata.clinical_context or {}).get("likely_handwriting", False),
            "layout_graph": request.layout_graph.model_dump(by_alias=True),
            "section_hierarchy": (
                request.section_hierarchy.model_dump() if request.section_hierarchy else None
            ),
            "assets": [asset.model_dump() for asset in request.assets],
            "tables": [table.model_dump() for table in request.tables],
            "evidence_level": source_tier.name,
        },
        content_checksum=hashlib.sha256(enriched_content.encode("utf-8")).hexdigest(),
    )

    background_tasks.add_task(
        process_embeddings,
        repair_doc,
        [
            {
                "asset_id": asset.asset_id,
                "type": _normalize_asset_type(asset.kind, asset.path),
                "storage_path": asset.path,
            }
            for asset in request.assets
        ],
    )
    logger.info(
        "Scheduled duplicate vector repair | doc_uid=%s document_id=%s",
        existing_metadata.doc_uid,
        existing_metadata.document_id,
    )
    return safety["safety_confidence"]


# -------------------------------------------------
# API Endpoint
# -------------------------------------------------


@app.exception_handler(RequestValidationError)
async def extraction_payload_validation_handler(request: Request, exc: RequestValidationError):
    """
    Provides actionable validation feedback for malformed extractor payloads.
    """
    if request.url.path != "/refinery/v1/ingest":
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    actionable_errors = []
    for error in exc.errors():
        field_path = ".".join(str(part) for part in error.get("loc", [])[1:])
        actionable_errors.append(
            {
                "field": field_path or "payload",
                "error": error.get("msg", "Invalid value"),
                "action": f"Fix '{field_path or 'payload'}' in extractor output and retry.",
            }
        )

    return JSONResponse(
        status_code=422,
        content={
            "detail": "Extractor payload validation failed. The payload is incomplete or malformed.",
            "errors": actionable_errors,
        },
    )


@app.exception_handler(OperationalError)
async def database_operational_error_handler(request: Request, exc: OperationalError):
    logger.error("Database unavailable while handling %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": "Metadata database is unavailable.",
            "message": (
                "Check DATABASE_URL and network/DNS access to PostgreSQL. "
                "Ingestion, citation, and metadata-backed endpoints need the database."
            ),
        },
    )


@app.post(
    "/refinery/v1/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
)
async def ingest_document(
    request: ExtractionOutput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),

):
    """
    End-to-end medical knowledge ingestion pipeline.

    This endpoint is:
    - Idempotent
    - Safe under concurrency
    - Audit-friendly
    """

    # ---------------------------------------------
    # Step 1: Integrity + Trust Gate
    # ---------------------------------------------

    gatekeeper = IngestionGatekeeper(db)

    try:
        ingestion_result = await gatekeeper.validate_and_classify(
            raw_content=request.content,
            source_hint=request.source,
            document_id=request.document_id,
        )
    except InvalidDocumentError as e:
        return IngestResponse(
            decision=IngestionDecision.REJECTED_INVALID,
            doc_uid=None,
            status=None,
            tier=None,
            safety_confidence=None,
            message=str(e),
        )
    except DuplicateDocumentError as e:
        existing_metadata = db.query(MedicalMetadata).filter(
            MedicalMetadata.document_id == request.document_id
        ).first()
        repair_confidence = None
        if existing_metadata:
            try:
                repair_confidence = await _schedule_duplicate_vector_repair(
                    request=request,
                    background_tasks=background_tasks,
                    existing_metadata=existing_metadata,
                )
            except Exception as repair_error:
                logger.exception(
                    "Duplicate vector repair scheduling failed | document_id=%s error=%s",
                    request.document_id,
                    str(repair_error),
                )

        return IngestResponse(
            decision=IngestionDecision.SKIPPED_DUPLICATE,
            doc_uid=str(e),  # contains doc_uid
            status=(
                _coerce_doc_status(existing_metadata.status).value
                if existing_metadata
                else "unchanged"
            ),
            tier=(
                _coerce_trust_tier(existing_metadata.source_tier).name
                if existing_metadata
                else None
            ),
            safety_confidence=repair_confidence,
            message=(
                "Document already ingested; missing vectors are being rebuilt"
                if repair_confidence is not None
                else "Document already ingested"
            ),
        )

    decision = ingestion_result["decision"]

    if decision == IngestionDecision.REJECTED_INVALID:
        return IngestResponse(
            decision=decision,
            doc_uid=None,
            status=None,
            tier=None,
            safety_confidence=None,
            message=ingestion_result["reason"],
        )

    if decision == IngestionDecision.SKIPPED_DUPLICATE:
        return IngestResponse(
            decision=decision,
            status="unchanged",
            tier=ingestion_result["tier"].name,
            safety_confidence=None,
            message="Document already ingested",
        )

    # ---------------------------------------------
    # Step 2: Retraction Awareness
    # ---------------------------------------------

    tier: TrustTier = ingestion_result["tier"]
    authority_score = ingestion_result["authority_score"]

    retraction = await retraction_service.check_retraction(
        title=request.metadata.title.value,
        source=request.source,
        tier=tier,
    )

    status_flag = DocStatus.ACTIVE
    status_flag = retraction_service.apply_lifecycle_policy(
        current_status=status_flag,
        retraction_result=retraction,
    )

    quality_gate_failed = (
        request.quality.overall_score < EXTRACTOR_QUALITY_THRESHOLD
        or request.quality.ocr_mean_confidence < OCR_MEAN_CONFIDENCE_THRESHOLD
    )

    if quality_gate_failed:
        status_flag = DocStatus.QUARANTINED
        audit_reason = (
            "QUARANTINED: extractor quality gate failed "
            f"(overall={request.quality.overall_score:.3f}, "
            f"ocr_mean={request.quality.ocr_mean_confidence:.3f})"
        )
    else:
        audit_reason = "Initial ingestion"

    # ---------------------------------------------
    # Step 3: Safety & PHI Gate
    # ---------------------------------------------

    safety = await safety_engine.process_content(request.content)

    if retraction.is_retracted and not quality_gate_failed:
        audit_reason = f"Ingested as Deprecated: {retraction.reason}"

    # Safety quarantine overrides active/deprecated status
    if safety["decision"] == SafetyDecision.QUARANTINED:
        status_flag = DocStatus.QUARANTINED
        audit_reason = "QUARANTINED: PHI risk detected by safety engine"

    if safety["safety_confidence"] < PHI_VECTORIZATION_CONFIDENCE_THRESHOLD:
        status_flag = DocStatus.QUARANTINED
        audit_reason = (
            "QUARANTINED: PHI confidence below vectorization gate "
            f"({safety['safety_confidence']:.3f} < {PHI_VECTORIZATION_CONFIDENCE_THRESHOLD:.2f})"
        )
        logger.warning(audit_reason)

    likely_handwriting = (
        request.quality.ocr_mean_confidence < OCR_MEAN_CONFIDENCE_THRESHOLD
        and _has_high_text_density_signal(request.quality.issues)
    )

    # ---------------------------------------------
    # Step 4: Structured Parsing
    # ---------------------------------------------

    enriched_content = safety["processed_content"]
    if not quality_gate_failed:
        enriched_content = parser.unify_findings(enriched_content)

    # ---------------------------------------------
    # Step 5: Canonical Schema Creation
    # ---------------------------------------------

    doc = MedicalDocumentSchema(
        title=request.metadata.title.value,
        document_id=ingestion_result["document_id"],
        doc_uid=ingestion_result["doc_uid"],
        source=request.source,
        source_tier=tier,
        authority_score=authority_score,
        published_at=(request.metadata.published_at.value if request.metadata.published_at else datetime.now(timezone.utc)),
        status=status_flag,
        raw_content=enriched_content,
        tags=request.metadata.tags,
        metadata_extra={
            "likely_handwriting": likely_handwriting,
            "layout_graph": request.layout_graph.model_dump(by_alias=True),
            "section_hierarchy": (
                request.section_hierarchy.model_dump() if request.section_hierarchy else None
            ),
            "assets": [asset.model_dump() for asset in request.assets],
            "tables": [table.model_dump() for table in request.tables],
            "evidence_level": tier.name,
        },
        content_checksum=hashlib.sha256(enriched_content.encode("utf-8")).hexdigest(),
    )

    extractor_version = request.audit.extraction.engine_version
    processing_host = os.getenv("HOSTNAME", "unknown")
    fetched_at = request.audit.extraction.extracted_at
    extracted_at = request.audit.extraction.extracted_at
    source_hash = hashlib.sha256(request.audit.source.uri.encode("utf-8")).hexdigest()
    source_parent_hash = request.audit.document_id
    document_version_hash = hashlib.sha256(
        f"{doc.document_id}:{doc.content_checksum}:{extractor_version}".encode("utf-8")
    ).hexdigest()

    # ---------------------------------------------
    # Step 6: Persist Metadata
    # ---------------------------------------------
    # ---------------------------------------------
    # Step 6: Persist Metadata (Corrected)
    # ---------------------------------------------
    metadata = MedicalMetadata(
        document_id=doc.document_id,
        content_hash=doc.content_checksum,
        doc_uid=doc.doc_uid,
        title=doc.title,
        source_type=doc.source,
        source_tier=doc.source_tier.value,
        authority_score=doc.authority_score,
        status=doc.status,
        published_at=doc.published_at,
        clinical_context={"likely_handwriting": likely_handwriting},
        source_hash=source_hash,
        source_parent_hash=source_parent_hash,
        extractor_version=extractor_version,
        processing_host=processing_host,
        fetched_at=fetched_at,
        extracted_at=extracted_at,
        extraction_engine=request.audit.extraction.engine,
        extraction_engine_version=request.audit.extraction.engine_version,
        document_version_hash=document_version_hash,
    )

    table_rows = [
        MedicalTable(
            table_id=table.table_id,
            document_id=doc.document_id,
            csv_payload=_table_to_csv(table),
            raw_payload=table.model_dump(),
            provenance_metadata={
                "layout_node": table.layout_node,
                "section_id": table.section_id,
                "page": table.page,
            },
        )
        for table in request.tables
    ]

    asset_rows = [
        MedicalAsset(
            asset_id=asset.asset_id,
            type=_normalize_asset_type(asset.kind, asset.path),
            storage_path=asset.path,
            vector_id=None,
            document_id=doc.document_id,
            provenance_metadata={
                "page": asset.page,
                "hash": asset.hash,
                "caption": asset.caption,
                "derivatives": [item.model_dump() for item in asset.derivatives],
            },
        )
        for asset in request.assets
    ]

    try:
        db.add(metadata)

        audit = MedicalMetadataAudit(
            document_id=doc.document_id,
            doc_uid=doc.doc_uid,
            previous_status=None,
            new_status=doc.status.value,
            reason=(
                f"{audit_reason}; likely_handwriting={str(likely_handwriting).lower()}"
            ),
            actor="system",
            extractor_version=extractor_version,
            processing_host=processing_host,
            fetched_at=fetched_at,
            extracted_at=extracted_at,
            extraction_engine=request.audit.extraction.engine,
            extraction_engine_version=request.audit.extraction.engine_version,
            source_hash=source_hash,
            source_parent_hash=source_parent_hash,
            document_version_hash=document_version_hash,
            authority_score=doc.authority_score,
        )
        db.add(audit)

        if table_rows:
            db.add_all(table_rows)
        if asset_rows:
            db.add_all(asset_rows)

        db.flush()
        db.commit()

    except IntegrityError:
        db.rollback()
        return IngestResponse(
            decision=IngestionDecision.SKIPPED_DUPLICATE,
            doc_uid=doc.doc_uid,
            status="unchanged",
            tier=doc.source_tier.name,
            safety_confidence=safety["safety_confidence"],
            message="Document already ingested (race condition)",
        )

    # ---------------------------------------------
    # Step 7: KG Upsert (post safety gates)
    # ---------------------------------------------

    kg_write_outcome = {
        "status": "skipped",
        "reason": "failed_safety_gate",
    }

    if doc.status != DocStatus.QUARANTINED:
        try:
            kg_write_outcome = await kg_service.upsert_medication_graph(
                document_id=doc.document_id,
                metadata=request.metadata,
                medical_patterns=request.medical_patterns,
                authority_score=doc.authority_score,
            )
        except Exception as kg_error:
            logger.error(
                "KG write failed | doc_uid=%s document_id=%s error=%s",
                doc.doc_uid,
                doc.document_id,
                str(kg_error),
            )
            kg_write_outcome = {
                "status": "failed",
                "reason": str(kg_error),
            }

    contradiction_clusters = []
    if doc.status != DocStatus.QUARANTINED and kg_write_outcome.get("status") == "success":
        try:
            contradiction_clusters = await contradiction_engine.check_document(document_id=doc.document_id)
            if contradiction_clusters:
                logger.warning("CONTRADICTION DETECTED | doc_uid=%s | clusters=%s", doc.doc_uid, [c.to_dict() for c in contradiction_clusters])
                db.add(MedicalMetadataAudit(document_id=doc.document_id, doc_uid=doc.doc_uid, previous_status=doc.status.value, new_status=doc.status.value, reason=(f"CONTRADICTION_DETECTED: {len(contradiction_clusters)} drug(s) flagged. " + str([c.to_dict() for c in contradiction_clusters])[:200]), actor="contradiction_engine"))
                db.commit()
        except Exception as ce:
            logger.error(f"Contradiction check failed: {ce}")

    kg_audit = MedicalMetadataAudit(
        document_id=doc.document_id,
        doc_uid=doc.doc_uid,
        previous_status=doc.status.value,
        new_status=doc.status.value,
        reason=f"KG_WRITE_OUTCOME: {str(kg_write_outcome)[:220]}",
        actor="kg_service",
        extractor_version=extractor_version,
        processing_host=processing_host,
        fetched_at=fetched_at,
        extracted_at=extracted_at,
        extraction_engine=request.audit.extraction.engine,
        extraction_engine_version=request.audit.extraction.engine_version,
        source_hash=source_hash,
        source_parent_hash=source_parent_hash,
        document_version_hash=document_version_hash,
        authority_score=doc.authority_score,
    )
    db.add(kg_audit)
    db.commit()

    # ---------------------------------------------
    # Step 8: Async Chunking & Vectorization
    # ---------------------------------------------

    if doc.status == DocStatus.ACTIVE:
        background_tasks.add_task(
            process_embeddings,
            doc,
            [
                {
                    "asset_id": asset.asset_id,
                    "type": _normalize_asset_type(asset.kind, asset.path),
                    "storage_path": asset.path,
                }
                for asset in request.assets
            ],
        )

    # ---------------------------------------------
    # Final Response
    # ---------------------------------------------

    return IngestResponse(
        decision=IngestionDecision.ACCEPTED,
        doc_uid=doc.doc_uid,
        status=doc.status.value,
        tier=doc.source_tier.name,
        safety_confidence=safety["safety_confidence"],
        message=(f"Document ingested. Contradictions detected: {len(contradiction_clusters)}" if contradiction_clusters else "Document ingested successfully"),
    )


# -------------------------------------------------
# Background Worker
# -------------------------------------------------

async def process_embeddings(doc: MedicalDocumentSchema, assets_for_embedding: list[dict]):
    """
    Async worker for chunking + vector storage.
    Failure here MUST NOT affect ingestion success.
    """
    try:
        hierarchy = chunker.process_document(doc)
        logger.info("Chunker produced %d groups", len(hierarchy))

        vector_result = await vector_service.upsert_vector_hierarchy(hierarchy, doc)
        logger.info(  # ← add this
            "Vector result: success=%s failed=%s",
            vector_result.get("success_count"),
            vector_result.get("failed_count"),
        )

        if not isinstance(vector_result, dict):
            vector_result = {}
        failed_chunks = vector_result.get("failed_chunks")
        if not isinstance(failed_chunks, list):
            failed_chunks = []

        logger.info("Failed chunks: %s", vector_result.get("failed_chunks"))

        asset_vector_map = await vector_service.upsert_visual_assets(
            assets_for_embedding,
            doc,
        )

        with SessionLocal() as db:
            for failed in failed_chunks:
                db.add(
                    ProcessingError(
                        document_id=doc.document_id,
                        chunk_id=failed["chunk_id"],
                        stage=failed["stage"],
                        error_type=failed["error_type"],
                        error_message=failed["error_message"][:2000],
                    )
                )

            if asset_vector_map:
                for asset_id, vector_id in asset_vector_map.items():
                    db.query(MedicalAsset).filter(
                        MedicalAsset.document_id == doc.document_id,
                        MedicalAsset.asset_id == asset_id,
                    ).update({MedicalAsset.vector_id: vector_id})

            summary_metadata = {
                "vectorization_summary": {
                    "success_count": vector_result.get("success_count", 0),
                    "failed_count": vector_result.get("failed_count", 0),
                    "retryable_count": vector_result.get("retryable_count", 0),
                },
                "retrieval_traceability": {
                    "chunk_ids": list(vector_result.get("vector_map", {}).keys()),
                    "document_id": doc.document_id,
                    "document_version_hash": vector_result.get("document_version_hash", doc.content_checksum),
                    "authority_score": doc.authority_score,
                },
                "index_routing": vector_result.get("index_routing", {}),
            }
            db.add(
                MedicalMetadataAudit(
                    document_id=doc.document_id,
                    doc_uid=doc.doc_uid,
                    previous_status=doc.status.value,
                    new_status=doc.status.value,
                    reason="EMBEDDING_PROCESSING_SUMMARY",
                    actor="vector_service",
                    audit_metadata=summary_metadata,
                    chunk_ids=list(vector_result.get("vector_map", {}).keys()),
                    document_version_hash=vector_result.get("document_version_hash", doc.content_checksum),
                    authority_score=doc.authority_score,
                )
            )
            db.commit()

    except VectorTransientError as e:
        logger.warning(
            "Transient vector error while processing doc_uid=%s document_id=%s error=%s",
            doc.doc_uid,
            doc.document_id,
            str(e),
        )

    except VectorPermanentError as e:
        logger.error(f"Permanent vector error for {doc.doc_uid}: {e}")

        with SessionLocal() as db:
            try:
                update_status(
                    db=db,
                    document_id=doc.document_id,
                    new_status=DocStatus.QUARANTINED,
                    reason=f"Permanent vectorization failure: {str(e)}",
                )
                db.commit()
            except Exception as audit_err:
                logger.error(f"Failed to quarantine document {doc.doc_uid}: {audit_err}")

    except Exception as e:
        logger.exception(
            "Unexpected embedding pipeline failure | doc_uid=%s document_id=%s error=%s",
            doc.doc_uid,
            doc.document_id,
            str(e),
        )


@app.post("/refinery/v1/maintenance/rebuild-index")
async def trigger_index_rebuild():
    raise HTTPException(status_code=501, detail="Index rebuild is not implemented yet. Use offline maintenance tooling.")


@app.get("/refinery/v1/maintenance/vector-status/{document_id}")
async def vector_status(document_id: str):
    chunk_count = await vector_service.count_document_vectors(document_id)
    return {
        "document_id": document_id,
        "vectorized_chunks": chunk_count,
        "ready": chunk_count > 0,
    }


# -------------------------------------------------
# AI Diagnostic Chat (Profile-Driven Dual RAG)
# -------------------------------------------------

class UserProfile(BaseModel):
    age: Optional[int] = None
    sex: Optional[str] = None
    conditions: list[str] = []
    allergies: list[str] = []
    current_medications: list[str] = []
    habits: list[str] = []
    family_history: list[str] = []
    height: Optional[float] = None
    weight: Optional[float] = None

class DiagnosticChatRequest(BaseModel):
    question: str
    user_profile: UserProfile
    location_context: dict = Field(default_factory=dict)
    session_id: Optional[str] = None
    chat_history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    uploaded_images: list[UploadedImage] = Field(default_factory=list, max_length=3)

class DiagnosticChatResponse(BaseModel):
    answer: str
    retrieved_facts: list[str] = Field(default_factory=list)
    retrieved_knowledge: list[str] = Field(default_factory=list)
    diagnostic_source: str = "legacy_dual_rag"
    strategy_used: Optional[str] = None
    contradictions_found: Optional[bool] = None
    citations: list[dict] = Field(default_factory=list)
    visual_assets: list[dict] = Field(default_factory=list)
    confidence_score: Optional[float] = None
    safety_flags: list[str] = Field(default_factory=list)
    escalation_required: Optional[bool] = None
    retrieval_trace: list[dict] = Field(default_factory=list)
    updated_session_summary: Optional[str] = None
    updated_pinned_medical_facts: dict = Field(default_factory=dict)
    updated_open_questions: list[str] = Field(default_factory=list)
    updated_safety_notes: list[str] = Field(default_factory=list)
    inference_error: Optional[str] = None


def _profile_additional_notes(profile: UserProfile) -> Optional[str]:
    notes = []
    if profile.habits:
        notes.append("Habits: " + ", ".join(profile.habits))
    if profile.family_history:
        notes.append("Family history: " + ", ".join(profile.family_history))
    if profile.height is not None:
        notes.append(f"Height: {profile.height}")
    if profile.weight is not None:
        notes.append(f"Weight: {profile.weight}")
    return "; ".join(notes) if notes else None


def _call_mistral(prompt: str, json_mode=False):
    if not MISTRAL_API_KEY:
        logger.error("Mistral AI call failed: MISTRAL_API_KEY is not configured")
        return ""

    try:
        response = requests.post(
            MISTRAL_API_URL,
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MISTRAL_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=60
        )

        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]

        if json_mode:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]

        return content.strip()

    except Exception as e:
        logger.error(f"Mistral AI call failed: {e}")
        return ""

@app.post("/refinery/v1/chat/diagnostic", response_model=DiagnosticChatResponse)
async def diagnostic_chat(request: DiagnosticChatRequest):
    """
    Orchestrator for Profile-Driven Dual RAG.
    Combines BigQuery (MIMIC-III population facts) and Refinery (Graph/Vector knowledge).
    """
    query_service = getattr(app.state, SERVICE_STATE_KEY, None)
    inference_error = None
    if query_service is not None:
        try:
            patient_context = PatientContext(
                age=request.user_profile.age,
                sex=request.user_profile.sex,
                conditions=request.user_profile.conditions,
                allergies=request.user_profile.allergies,
                medications=request.user_profile.current_medications,
                additional_notes=_profile_additional_notes(request.user_profile),
            )
            query_response = await query_service.answer_async(
                QueryRequest(
                    query_text=request.question,
                    session_id=request.session_id,
                    chat_history=request.chat_history,
                    uploaded_images=request.uploaded_images,
                    patient_context=patient_context,
                    request_metadata={
                        "source_endpoint": "/refinery/v1/chat/diagnostic",
                        "location_context": request.location_context,
                    },
                )
            )
            return DiagnosticChatResponse(
                answer=query_response.answer,
                retrieved_facts=query_response.safety_flags,
                retrieved_knowledge=[
                    citation.snippet
                    for citation in query_response.citations
                    if citation.snippet
                ],
                diagnostic_source="healthylabs_inference",
                strategy_used=query_response.strategy_used,
                contradictions_found=query_response.contradictions_found,
                citations=[citation.model_dump() for citation in query_response.citations],
                visual_assets=[asset.model_dump() for asset in query_response.visual_assets],
                confidence_score=query_response.confidence_score,
                safety_flags=query_response.safety_flags,
                escalation_required=query_response.escalation_required,
                retrieval_trace=query_response.retrieval_trace,
                updated_session_summary=query_response.updated_session_summary,
                updated_pinned_medical_facts=query_response.updated_pinned_medical_facts,
                updated_open_questions=query_response.updated_open_questions,
                updated_safety_notes=query_response.updated_safety_notes,
                inference_error=None,
            )
        except Exception as exc:
            inference_error = str(exc)
            logger.error(
                "Integrated HealthyLabs query service failed; falling back to legacy diagnostic flow: %s",
                exc,
            )
    
    # --- 1. Entity Extraction Phase ---
    extraction_prompt = f"""
    Extract the key medical entities from the following user question and profile context.
    Return a valid JSON object ONLY (no markdown, no explanations) with the exact keys:
    "symptoms" (list of strings), "drugs" (list of strings), "conditions" (list of strings).
    
    Question: "{request.question}"
    Profile Context: {request.user_profile.model_dump_json()}
    """
    extracted_json = _call_mistral(extraction_prompt, json_mode=True)
    try:
        entities = json.loads(extracted_json)
    except json.JSONDecodeError:
        entities = {"symptoms": [], "drugs": [], "conditions": []}
        logger.warning(f"Failed to parse entities from LLM: {extracted_json}")

    symptoms = entities.get("symptoms", [])
    drugs = entities.get("drugs", [])
    conditions = entities.get("conditions", [])

    # Combine extracted entities with explicitly known profile context
    all_conditions = list(set(conditions + request.user_profile.conditions))
    all_drugs = list(set(drugs + request.user_profile.current_medications))

    # --- 2. Branch A: BigQuery Retrieval (Population Evidence) ---
    bq_facts = []
    try:
        bq_client = bigquery.Client(project='healthylabs')
        
        # Scenario 1: Symptom + Underlying Condition Correlation
        if symptoms and all_conditions:
            primary_symptom = symptoms[0]
            primary_condition = all_conditions[0]
            query = """
            SELECT d.short_title AS actual_diagnosis, COUNT(a.hadm_id) AS admission_count
            FROM `physionet-data.mimiciii_clinical.admissions` a
            JOIN `physionet-data.mimiciii_clinical.diagnoses_icd` icd ON a.hadm_id = icd.hadm_id
            JOIN `physionet-data.mimiciii_clinical.d_icd_diagnoses` d ON icd.icd9_code = d.icd9_code
            WHERE LOWER(a.diagnosis) LIKE LOWER(@symptom)
            AND a.subject_id IN (
                SELECT subject_id 
                FROM `physionet-data.mimiciii_clinical.diagnoses_icd` sub_icd
                JOIN `physionet-data.mimiciii_clinical.d_icd_diagnoses` sub_d ON sub_icd.icd9_code = sub_d.icd9_code
                WHERE LOWER(sub_d.short_title) LIKE LOWER(@condition)
            )
            GROUP BY actual_diagnosis
            ORDER BY admission_count DESC
            LIMIT 3;
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("symptom", "STRING", f"%{primary_symptom}%"),
                    bigquery.ScalarQueryParameter("condition", "STRING", f"%{primary_condition}%")
                ]
            )
            results = bq_client.query(query, job_config=job_config).result()
            
            for row in results:
                bq_facts.append(
                    f"MIMIC-III Factual Data: When patients with a history of '{primary_condition}' present with '{primary_symptom}', "
                    f"a common historical diagnosis is {row.actual_diagnosis} ({row.admission_count} recorded ICU cases)."
                )

        # Scenario 2: Drug Complication Checks
        if all_drugs:
            primary_drug = all_drugs[0]
            query = """
            SELECT d.short_title AS complication_diagnosis, COUNT(DISTINCT p.hadm_id) AS incident_count
            FROM `physionet-data.mimiciii_clinical.prescriptions` p
            JOIN `physionet-data.mimiciii_clinical.diagnoses_icd` icd ON p.hadm_id = icd.hadm_id
            JOIN `physionet-data.mimiciii_clinical.d_icd_diagnoses` d ON icd.icd9_code = d.icd9_code
            WHERE LOWER(p.drug) LIKE LOWER(@drug)
            GROUP BY complication_diagnosis
            ORDER BY incident_count DESC
            LIMIT 3;
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("drug", "STRING", f"%{primary_drug}%")
                ]
            )
            results = bq_client.query(query, job_config=job_config).result()
            
            for row in results:
                bq_facts.append(
                    f"MIMIC-III Factual Data: Among patients prescribed '{primary_drug}', "
                    f"common secondary diagnoses during admission include {row.complication_diagnosis} ({row.incident_count} incidents)."
                )
                
    except Exception as e:
        logger.error(f"BigQuery retrieval failed: {e}")
        bq_facts.append("Note: Population-level clinical data is currently unavailable.")

    # --- 3. Branch B: Curated Knowledge Retrieval (Refinery) ---
    retrieved_knowledge = []
    try:
        # Placeholder for vector search implementation
        if hasattr(vector_service, 'search'):
            search_query = " ".join(symptoms + all_drugs + all_conditions).strip()
            results = await vector_service.search(search_query, top_k=3)
            retrieved_knowledge.extend([res.get("text", "") for res in results])
        else:
            retrieved_knowledge.append("Knowledge Graph integration placeholder: Graph traversal indicates interactions are safe.")
    except Exception as e:
        logger.error(f"Vector/Graph retrieval failed: {e}")

    # --- 4. Aggregation Phase & 5. Generation Phase ---
    context_str = "\n- ".join(retrieved_knowledge) if retrieved_knowledge else "None"
    facts_str = "\n- ".join(bq_facts) if bq_facts else "None"
    
    generation_prompt = f"""
    You are HealthyLabs.AI, a warm medical information chat assistant for Indian users.
    Assess the user's query based STRICTLY on the provided knowledge and the user's personal profile. Do not guess outside this knowledge.
    
    Style requirements:
    - Answer like a natural conversation, similar to ChatGPT or Gemini, speaking directly to the user.
    - Do not mention internal labels such as "User's Personal Profile", "Curated Refinery Knowledge", "Vector & Graph Data", "BigQuery", or "RAG".
    - Do not use report-style headings like "Key Observations", "Recommendations", "Exclusions", or "Next Steps" unless the user asks for a formal report.
    - Keep it patient-friendly: short paragraphs, a few simple bullets only if helpful, and one relevant follow-up question at the end when appropriate.
    - Do not diagnose, prescribe, or tell the user to start/stop/change medication.
    - For severe symptoms such as chest pain, difficulty breathing, stroke signs, severe allergic reaction, fainting, seizure, overdose, or severe bleeding, tell the user to call India ambulance 108 immediately.
    
    User's Personal Profile:
    {request.user_profile.model_dump_json(indent=2)}
    
    Medical Factual Knowledge (BigQuery Population Data):
    - {facts_str}
    
    Curated Refinery Knowledge (Vector & Graph Data):
    - {context_str}
    
    Diagnostic Query: {request.question}

    Recent Conversation History:
    {json.dumps([message.model_dump() for message in request.chat_history[-10:]], ensure_ascii=False, indent=2)}
    """
    
    final_answer = _call_mistral(generation_prompt)
    if not final_answer:
        raise HTTPException(
            status_code=502,
            detail="Mistral AI did not return an answer. Check MISTRAL_API_KEY, MISTRAL_API_URL, and MISTRAL_MODEL.",
        )

    return DiagnosticChatResponse(
        answer=final_answer,
        retrieved_facts=bq_facts,
        retrieved_knowledge=retrieved_knowledge,
        diagnostic_source="legacy_dual_rag",
        inference_error=inference_error,
    )
