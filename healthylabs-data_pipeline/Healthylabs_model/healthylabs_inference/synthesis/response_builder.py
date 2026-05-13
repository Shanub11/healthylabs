"""Grounded response synthesis with citation and visual evidence mapping."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, field
from typing import Any

from healthylabs_inference.api.request_models import Citation, QueryRequest, VisualAsset
from healthylabs_inference.core.config import Settings
from healthylabs_inference.core.database_clients import PostgresCitationClient
from healthylabs_inference.core.llm_client import GeminiClient
from healthylabs_inference.orchestrator.prompts import SYNTHESIS_PROMPT, object_to_json
from healthylabs_inference.retrieval.models import RetrievedChunk
from healthylabs_inference.retrieval.strategies.visual import VisualResult


@dataclass(slots=True)
class BuiltResponse:
    answer: str
    citations: list[Citation]
    visual_assets: list[VisualAsset] = field(default_factory=list)


@dataclass(slots=True)
class ResponseBuilder:
    llm_client: GeminiClient
    citation_client: PostgresCitationClient
    settings: Settings

    def build(
        self,
        *,
        request: QueryRequest,
        chunks: list[RetrievedChunk],
        contradictions_found: bool,
        safety_flags: list[str],
        patient_specific_kg_facts: list[dict[str, Any]] | None = None,
        visual_results: list[VisualResult] | None = None,
    ) -> BuiltResponse:
        visual_results = visual_results or []
        uploaded_images = _decode_uploaded_images(request.uploaded_images)
        if not chunks and not visual_results and not uploaded_images:
            return BuiltResponse(
                answer=(
                    "I couldn’t find enough trusted HealthyLabs evidence to answer this confidently. "
                    "Please check with a qualified healthcare professional, especially if symptoms are severe, "
                    "new, worsening, or persistent."
                ),
                citations=[],
                visual_assets=[],
            )
        citations = self._build_citations(chunks)
        evidence = _build_evidence(chunks, citations, patient_specific_kg_facts or [])
        image_bytes_for_gemini: list[bytes] = []
        visual_assets_for_response: list[VisualAsset] = []
        for result in visual_results:
            if result.image_bytes:
                image_bytes_for_gemini.append(result.image_bytes)
                evidence.append(
                    {
                        "kind": "visual_asset",
                        "caption": result.caption,
                        "similarity_score": result.score,
                        "doc_uid": result.doc_uid,
                    }
                )
            if result.presigned_url:
                visual_assets_for_response.append(
                    VisualAsset(
                        url=result.presigned_url,
                        alt_text=result.caption or "Medical reference image",
                        source_document=result.doc_uid,
                    )
                )
        for uploaded in uploaded_images:
            image_bytes_for_gemini.append(uploaded["bytes"])
            evidence.append(
                {
                    "kind": "user_uploaded_image",
                    "filename": uploaded["filename"],
                    "content_type": uploaded["content_type"],
                    "note": (
                        "The user attached this image with the current question. "
                        "Use it only for visual assessment and severity triage; do not diagnose from the image alone."
                    ),
                }
            )
        recent_history = request.chat_history[-self.settings.synthesis_chat_history_window :]
        prompt = SYNTHESIS_PROMPT.format(
            query_text=request.query_text,
            session_summary_json=object_to_json(request.session_summary or "No prior context."),
            pinned_medical_facts_json=object_to_json(request.pinned_medical_facts),
            open_questions_json=object_to_json(request.open_questions),
            safety_notes_json=object_to_json(request.safety_notes),
            chat_history_json=object_to_json([m.model_dump() for m in recent_history]),
            patient_context_json=object_to_json(request.patient_context or {}),
            contradictions_found=contradictions_found,
            safety_flags_json=object_to_json(safety_flags),
            evidence_json=object_to_json(evidence),
        )
        if image_bytes_for_gemini:
            answer = self.llm_client.generate_multimodal(
                prompt,
                image_bytes_list=image_bytes_for_gemini,
                temperature=0.15,
                max_output_tokens=1200,
            ).text
        else:
            answer = self.llm_client.generate(prompt, temperature=0.15, max_output_tokens=1200).text
        return BuiltResponse(
            answer=answer,
            citations=citations,
            visual_assets=visual_assets_for_response,
        )

    def _build_citations(self, chunks: list[RetrievedChunk]) -> list[Citation]:
        ordered_doc_uids = []
        for chunk in chunks:
            if chunk.doc_uid and chunk.doc_uid not in ordered_doc_uids:
                ordered_doc_uids.append(chunk.doc_uid)
        metadata = self.citation_client.fetch_citations(ordered_doc_uids)
        citations: list[Citation] = []
        seen = set()
        for chunk in chunks:
            key = chunk.citation_key
            if key in seen:
                continue
            seen.add(key)
            doc_meta = metadata.get(chunk.doc_uid or "", {})
            citations.append(
                Citation(
                    ref_id=f"[{len(citations) + 1}]",
                    title=doc_meta.get("title"),
                    source=doc_meta.get("source"),
                    doc_uid=chunk.doc_uid,
                    document_id=doc_meta.get("document_id") or chunk.document_id,
                    source_tier=doc_meta.get("source_tier") or chunk.tier,
                    authority_score=doc_meta.get("authority_score") or chunk.authority_score,
                    snippet=_snippet(chunk.text),
                )
            )
            if len(citations) >= 8:
                break
        return citations


def _build_evidence(
    chunks: list[RetrievedChunk],
    citations: list[Citation],
    patient_specific_kg_facts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    if patient_specific_kg_facts:
        evidence.append(
            {
                "kind": "patient_specific_kg_facts",
                "facts": patient_specific_kg_facts,
                "authority": "knowledge_graph_override",
            }
        )
    citation_by_key = {
        citation.doc_uid or citation.document_id or citation.ref_id: citation.ref_id for citation in citations
    }
    for chunk in chunks:
        ref = citation_by_key.get(chunk.doc_uid or chunk.document_id or chunk.chunk_id, "[?]")
        evidence.append(
            {
                "kind": "retrieved_chunk",
                "ref_id": ref,
                "atomic_chunk": chunk.text[:1_200],
                "clinical_context": (chunk.context_text or "")[:1_800],
                "authority_score": chunk.authority_score,
                "vector_score": chunk.vector_score,
                "metadata": chunk.context_metadata,
            }
        )
    return evidence


def _decode_uploaded_images(uploaded_images: list[Any]) -> list[dict[str, Any]]:
    decoded: list[dict[str, Any]] = []
    for image in uploaded_images:
        try:
            raw = base64.b64decode(image.data_base64, validate=True)
        except (binascii.Error, ValueError):
            continue
        if not raw:
            continue
        decoded.append(
            {
                "bytes": raw,
                "filename": image.filename,
                "content_type": image.content_type,
            }
        )
    return decoded


def _snippet(text: str, limit: int = 1000) -> str:
    collapsed = " ".join(text.split())
    return collapsed if len(collapsed) <= limit else f"{collapsed[: limit - 1]}…"
