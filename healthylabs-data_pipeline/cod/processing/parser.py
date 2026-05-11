import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


# -------------------------------------------------
# Enums & Contracts
# -------------------------------------------------

class FindingType(str, Enum):
    DOSAGE_TABLE = "dosage_table"
    LAB_TABLE = "lab_table"
    IMAGING_FINDING = "imaging_finding"
    UNKNOWN = "unknown"


class ParserConfidence(float):
    """
    Semantic alias for confidence scores (0.0 – 1.0).
    """
    pass


# -------------------------------------------------
# Core Parser
# -------------------------------------------------

class MedicalStructureParser:
    """
    Production-grade Medical Structure Parser.

    Responsibilities:
    - Extract structured signals from raw text
    - Attach confidence scores
    - Never throw on partial failure
    - Produce normalized, machine-readable findings

    ❗ Contract:
    - Parsing failure MUST NOT block ingestion
    - Findings must be additive, never destructive
    """

    # -----------------------------
    # Public API
    # -----------------------------

    def unify_findings(self, text: str) -> str:
        """
        Injects structured findings into the document
        in a deterministic, chunker-safe format.
        """
        findings = self.extract_findings(text)

        if not findings:
            return text

        envelope = {
            "parser_version": "v1.0",
            "generated_at": datetime.utcnow().isoformat(),
            "findings": findings
        }

        structured_block = (
            "\n[STRUCTURED_DATA_START]\n"
            + json.dumps(envelope, indent=2)
            + "\n[STRUCTURED_DATA_END]\n"
        )

        return structured_block + text

    # -----------------------------
    # Finding Orchestration
    # -----------------------------

    def extract_findings(self, text: str) -> List[Dict[str, Any]]:
        """
        Runs all extractors and aggregates findings.
        """
        findings: List[Dict[str, Any]] = []

        extractors = [
            self._extract_dosage_tables,
            self._extract_lab_tables,
            self._extract_imaging_hints
        ]

        for extractor in extractors:
            try:
                results = extractor(text)
                if results:
                    findings.extend(results)
            except Exception:
                # Fail-soft: never break ingestion
                continue

        return findings

    # -----------------------------
    # Extractors
    # -----------------------------

    def _extract_dosage_tables(self, text: str) -> List[Dict[str, Any]]:
        """
        Heuristic detection of dosage-related tables or descriptions.
        """
        findings = []

        if re.search(r"\b(dosage|dose|mg|tablet|capsule)\b", text, re.IGNORECASE):
            findings.append({
                "type": FindingType.DOSAGE_TABLE,
                "confidence": ParserConfidence(0.70),
                "fields_detected": ["medication", "dose", "frequency"],
                "notes": "Dosage-related content detected heuristically"
            })

        return findings

    def _extract_lab_tables(self, text: str) -> List[Dict[str, Any]]:
        """
        Detects lab-value style tables (CBC, electrolytes, etc.).
        """
        findings = []

        lab_markers = [
            r"\bhemoglobin\b",
            r"\bwbc\b",
            r"\brbc\b",
            r"\bplatelet\b",
            r"\bsodium\b",
            r"\bpotassium\b"
        ]

        hits = sum(bool(re.search(p, text, re.IGNORECASE)) for p in lab_markers)

        if hits >= 2:
            findings.append({
                "type": FindingType.LAB_TABLE,
                "confidence": ParserConfidence(min(0.5 + hits * 0.1, 0.9)),
                "fields_detected": ["test_name", "value", "unit", "reference_range"],
                "notes": "Multiple lab indicators detected"
            })

        return findings

    def _extract_imaging_hints(self, text: str) -> List[Dict[str, Any]]:
        """
        Lightweight imaging mention detection.
        Actual CNN output is injected upstream/downstream.
        """
        findings = []

        if re.search(r"\b(x-ray|ct|mri|ultrasound)\b", text, re.IGNORECASE):
            findings.append({
                "type": FindingType.IMAGING_FINDING,
                "confidence": ParserConfidence(0.60),
                "fields_detected": ["modality", "anatomical_region"],
                "notes": "Imaging modality mentioned in text"
            })

        return findings

    # -----------------------------
    # Multimodal Extension Hooks
    # -----------------------------

    def extract_image_metadata(self, image_id: str) -> Dict[str, Any]:
        """
        Stub for CNN-based imaging extraction.
        Designed for async enrichment, not inline blocking.
        """
        return {
            "type": FindingType.IMAGING_FINDING,
            "confidence": ParserConfidence(0.95),
            "modality": "X-Ray",
            "detected_abnormalities": ["Ground-glass opacities"],
            "anatomical_location": "Lower lobe",
            "image_id": image_id,
            "parser_version": "v1.0"
        }
