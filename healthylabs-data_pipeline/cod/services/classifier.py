import re
import json
from typing import Tuple, Dict, List, Optional
from pathlib import Path
from datetime import datetime
import tldextract
from urllib.parse import urlparse

from cod.core.models import TrustTier


class SourceClassificationResult:
    """
    Internal result object for explainability & auditing.
    """
    def __init__(
        self,
        tier: TrustTier,
        authority_score: float,
        confidence: float,
        matched_patterns: List[str],
        override_used: bool = False
    ):
        self.tier = tier
        self.authority_score = authority_score
        self.confidence = confidence
        self.matched_patterns = matched_patterns
        self.override_used = override_used

    def to_dict(self) -> Dict:
        return {
            "tier": self.tier.name,
            "authority_score": self.authority_score,
            "confidence": round(self.confidence, 3),
            "matched_patterns": self.matched_patterns,
            "override_used": self.override_used,
            "timestamp": datetime.utcnow().isoformat()
        }


class SourceClassifier:
    """
    Production-grade Source Classifier.

    Guarantees:
    - Deterministic classification
    - Explainable decisions
    - Confidence scoring
    - Config-driven patterns
    - Safe default behavior
    """

    DEFAULT_CONFIG = {
        "canonical": {
            "tier": TrustTier.CANONICAL,
            "authority_score": 1.0,
            "confidence": 0.95,
            "patterns": [
                r"fda\.gov",
                r"cdc\.gov",
                r"who\.int",
                r"pubmed",
                r"clinicaltrials\.gov",
                r"nih\.gov"
            ]
        },
        "evidence": {
            "tier": TrustTier.EVIDENCE,
            "authority_score": 0.7,
            "confidence": 0.85,
            "patterns": [
                r"nejm\.org",
                r"thelancet\.com",
                r"jamanetwork\.com",
                r"bmj\.com",
                r"mayoclinic\.org"
            ]
        },
        "exploratory": {
            "tier": TrustTier.EXPLORATORY,
            "authority_score": 0.3,
            "confidence": 0.6,
            "patterns": [
                r"blog",
                r"medium\.com",
                r"user_upload",
                r"lifestyle",
                r"forum",
                r"reddit\.com"
            ]
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)

    # ------------------------------------------------------------------
    # Public API (Backward Compatible)
    # ------------------------------------------------------------------

    def suggest_tier(self, source_name: str) -> Tuple[TrustTier, float]:
        """
        Backward-compatible API.

        Returns:
            (TrustTier, authority_score)
        """
        result = self.classify(source_name)
        return result.tier, result.authority_score

    # ------------------------------------------------------------------
    # New Production API
    # ------------------------------------------------------------------

    def classify(self, source_name: str) -> SourceClassificationResult:
        """
        Full classification with confidence and explainability.
        Structural classification using registered domain extraction.
        Prevents spoofed substring matches.
        """

        source_lower = source_name.lower().strip()

        # Normalize input (handle raw domains without scheme)
        if not source_lower.startswith(("http://", "https://")):
            source_lower = f"http://{source_lower}"

        parsed = urlparse(source_lower)

        # Extract registered domain (e.g., sub.fda.gov -> fda.gov)
        extracted = tldextract.extract(parsed.netloc)

        if not extracted.domain or not extracted.suffix:
            return SourceClassificationResult(
                tier=TrustTier.EXPLORATORY,
                authority_score=0.3,
                confidence=0.4,
                matched_patterns=[]
            )

        registered_domain = f"{extracted.domain}.{extracted.suffix}"

        matched_results: List[SourceClassificationResult] = []

        for cfg in self.config.values():
            matched_patterns = []
            for pattern in cfg["patterns"]:
                try:
                    if re.search(pattern, registered_domain, re.IGNORECASE):
                        matched_patterns.append(pattern)
                except re.error:
                    if pattern.lower() == registered_domain:
                        matched_patterns.append(pattern)

            if matched_patterns:
                matched_results.append(
                    SourceClassificationResult(
                        tier=cfg["tier"],
                        authority_score=cfg["authority_score"],
                        confidence=cfg["confidence"],
                        matched_patterns=matched_patterns
                    )
                )

        # Deterministic resolution: highest authority tier wins
        if matched_results:
            matched_results.sort(key=lambda r: r.tier.value)
            return matched_results[0]

        # Safe default (fail-closed, never assume authority)
        return SourceClassificationResult(
            tier=TrustTier.EXPLORATORY,
            authority_score=0.3,
            confidence=0.4,
            matched_patterns=[]
        )

    # ------------------------------------------------------------------
    # Temporal Handling (Section 2.3)
    # ------------------------------------------------------------------

    @staticmethod
    def get_recency_decay(published_year: int, tier: TrustTier) -> float:
        """
        Applies a soft decay based on evidence freshness.
        """
        current_year = datetime.utcnow().year
        age = current_year - published_year

        if tier == TrustTier.CANONICAL:
            return 0.9 if age > 5 else 1.0

        if tier == TrustTier.EVIDENCE:
            return 0.85 if age > 7 else 1.0

        return 1.0

    # ------------------------------------------------------------------
    # Config Loading
    # ------------------------------------------------------------------

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """
        Loads classification rules from JSON or falls back to defaults.
        """
        if not config_path:
            return self.DEFAULT_CONFIG

        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"SourceClassifier config not found: {config_path}")

        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        return self._normalize_config(raw)

    def _normalize_config(self, raw_config: Dict) -> Dict:
        """
        Ensures config integrity and type safety.
        """
        normalized = {}

        for key, cfg in raw_config.items():
            normalized[key] = {
                "tier": TrustTier[cfg["tier"]],
                "authority_score": float(cfg["authority_score"]),
                "confidence": float(cfg.get("confidence", 0.75)),
                "patterns": list(cfg["patterns"])
            }

        return normalized


"""
you must add:

Unit tests for:

FDA → Tier 1

Mayo Clinic → Tier 2

Blog → Tier 3

Unknown source → Tier 3 (default)

Snapshot test for to_dict()
"""