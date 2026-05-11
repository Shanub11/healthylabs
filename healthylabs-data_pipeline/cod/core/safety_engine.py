import os
import re
import logging
from typing import Dict, Any, Tuple, List
from datetime import datetime, timezone
from enum import Enum

from cod.core.models import DocStatus

logger = logging.getLogger("MedicalSafetyEngine")
logger.setLevel(logging.INFO)

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    _HAS_PRESIDIO = True
except Exception:  # optional dependency
    AnalyzerEngine = None
    AnonymizerEngine = None
    _HAS_PRESIDIO = False

try:
    import spacy
except Exception:  # optional dependency
    spacy = None


class SafetyDecision(str, Enum):
    PASSED = "passed"
    QUARANTINED = "quarantined"


class PHIRedaction:
    def __init__(self, entity: str, value: str, start: int, end: int, score: float = 1.0):
        self.entity = entity
        self.value = value
        self.start = start
        self.end = end
        self.score = score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity": self.entity,
            "start": self.start,
            "end": self.end,
            "score": round(self.score, 4),
        }


class MedicalSafetyEngine:
    PHI_PATTERNS = {
        "NAME": r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2}\b",
        "DOB": r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
        "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
        "PHONE": r"\b(?:\+?\d{1,3})?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "PATIENT_ID": r"\b(?:mrn|patient\s?id|record\s?id)[:\s]?[A-Z0-9\-]{4,15}\b",
        "ADDRESS": r"\b\d+\s[A-Z][a-z]+(?:\s(?:Street|St|Ave|Road|Rd|Blvd|Lane|Ln))\b",
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    }

    CLINICAL_LABELS = {
        "CHEMICAL", "DISEASE", "GENE_OR_GENE_PRODUCT",
        "SIMPLE_CHEMICAL", "ORGANISM", "CELL_TYPE",
    }

    PRESIDIO_WEIGHTS = {
        "PERSON": 0.15,
        "DATE_TIME": 0.10,
        "US_SSN": 0.40,
        "PHONE_NUMBER": 0.10,
        "MEDICAL_LICENSE": 0.30,
        "US_PASSPORT": 0.35,
        "EMAIL_ADDRESS": 0.10,
        "LOCATION": 0.10,
    }

    def __init__(self, settings):
        self.settings = settings
        self._using_presidio = False
        self._has_scispacy = False
        self._analyzer = None
        self._anonymizer = None
        self._sci_nlp = None

        if _HAS_PRESIDIO:
            self._analyzer = AnalyzerEngine()
            self._anonymizer = AnonymizerEngine()
            self._using_presidio = True

            scispacy_enabled = os.getenv("SCISPACY_ENABLED", "false").strip().lower() == "true"
            if scispacy_enabled and spacy is not None:
                try:
                    self._sci_nlp = spacy.load("en_core_sci_md")
                    self._has_scispacy = True
                except Exception:
                    logger.warning("scispaCy model en_core_sci_md unavailable; clinical span protection disabled")
            elif not scispacy_enabled:
                logger.info("scispaCy clinical span protection disabled by SCISPACY_ENABLED flag")

    @staticmethod
    def medical_denoise(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        text = re.sub(r'(?i)page\s+\d+(\s+of\s+\d+)?', '', text)
        for pattern in [
            r"(?i)this information is not intended as medical advice.*",
            r"(?i)all rights reserved.*",
            r"(?i)copyright\s+\d{4}.*",
        ]:
            text = re.sub(pattern, '', text)
        return re.sub(r'\s+', ' ', text).strip()

    def _get_protected_spans(self, text: str) -> set[tuple[int, int]]:
        if not self._has_scispacy or self._sci_nlp is None:
            return set()
        doc = self._sci_nlp(text)
        return {(ent.start_char, ent.end_char) for ent in doc.ents if ent.label_ in self.CLINICAL_LABELS}

    def _detect_phi_regex(self, text: str) -> Tuple[List[PHIRedaction], float]:
        redactions: List[PHIRedaction] = []
        total_risk = 0.0
        for entity, pattern in self.PHI_PATTERNS.items():
            for m in re.finditer(pattern, text):
                redactions.append(PHIRedaction(entity=entity, value=m.group(), start=m.start(), end=m.end(), score=1.0))
                total_risk += self.settings.PHI_WEIGHTS.get(entity, 0.05)
        return redactions, min(total_risk, 1.0)

    def _detect_phi_presidio(self, text: str) -> Tuple[str, List[PHIRedaction], float]:
        protected = self._get_protected_spans(text)
        raw = self._analyzer.analyze(text=text, language="en")
        filtered = []
        for r in raw:
            overlaps = any(not (r.end <= ps or r.start >= pe) for ps, pe in protected)
            if not overlaps:
                filtered.append(r)
        total_risk = min(sum(self.PRESIDIO_WEIGHTS.get(r.entity_type, 0.05) * r.score for r in filtered), 1.0)
        if filtered:
            anon = self._anonymizer.anonymize(text=text, analyzer_results=filtered)
            scrubbed = anon.text
        else:
            scrubbed = text
        reds = [PHIRedaction(r.entity_type, "", r.start, r.end, r.score) for r in filtered]
        return scrubbed, reds, total_risk

    def _redact_text(self, text: str, redactions: List[PHIRedaction]) -> str:
        for r in sorted(redactions, key=lambda x: x.start, reverse=True):
            text = text[:r.start] + f"[[{r.entity}_REDACTED]]" + text[r.end:]
        return text

    async def process_content(self, raw_content: str) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        denoised = self.medical_denoise(raw_content)

        if self._using_presidio:
            scrubbed, redactions, raw_risk = self._detect_phi_presidio(denoised)
        else:
            redactions, raw_risk = self._detect_phi_regex(denoised)
            scrubbed = self._redact_text(denoised, redactions)

        confidence = max(0.0, round(1.0 - (raw_risk * 0.5), 4))
        passed = confidence >= self.settings.HARD_CONFIDENCE_THRESHOLD

        if not passed:
            logger.warning(f"PHI QUARANTINE | confidence={confidence} | redactions={len(redactions)}")

        return {
            "processed_content": scrubbed,
            "decision": SafetyDecision.PASSED if passed else SafetyDecision.QUARANTINED,
            "status": DocStatus.ACTIVE if passed else DocStatus.QUARANTINED,
            "safety_confidence": confidence,
            "redaction_count": len(redactions),
            "redactions": [r.to_dict() for r in redactions],
            "audit_trail": {
                "denoised": True,
                "phi_detected": len(redactions) > 0,
                "raw_risk_score": raw_risk,
                "confidence_threshold": self.settings.HARD_CONFIDENCE_THRESHOLD,
                "scispacy_active": self._has_scispacy,
                "presidio_active": self._using_presidio,
                "timestamp": timestamp,
            }
        }
