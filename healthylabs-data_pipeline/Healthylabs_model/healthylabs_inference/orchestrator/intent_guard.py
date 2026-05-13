"""Safety-first medical intent guard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from healthylabs_inference.core.llm_client import GeminiClient
from healthylabs_inference.orchestrator.prompts import INTENT_GUARD_PROMPT

Intent = Literal["emergency", "research", "educational"]

_EMERGENCY_TERMS = (
    "chest pain",
    "can't breathe",
    "cannot breathe",
    "difficulty breathing",
    "problem in breathing",
    "shortness of breath",
    "suicidal",
    "kill myself",
    "overdose",
    "stroke",
    "face drooping",
    "severe bleeding",
    "unconscious",
    "anaphylaxis",
    "seizure",
)


@dataclass(frozen=True, slots=True)
class IntentDecision:
    intent: Intent
    reasoning: str
    source: str = "heuristic"


class IntentGuard:
    def __init__(self, llm_client: GeminiClient | None = None):
        self._llm = llm_client

    def classify(self, query_text: str) -> IntentDecision:
        heuristic = self._heuristic(query_text)
        if self._llm is None:
            return heuristic
        prompt = INTENT_GUARD_PROMPT.format(query_text=query_text)
        try:
            result = self._llm.generate_json(prompt, temperature=0.0, max_output_tokens=240)
        except (ValueError, TypeError, RuntimeError):
            return heuristic
        intent = result.get("intent", heuristic.intent)
        if intent not in {"emergency", "research", "educational"}:
            intent = heuristic.intent
        return IntentDecision(intent=intent, reasoning=str(result.get("reasoning", "")), source="llm")

    def _heuristic(self, query_text: str) -> IntentDecision:
        text = query_text.lower()
        if any(term in text for term in _EMERGENCY_TERMS):
            return IntentDecision(
                intent="emergency",
                reasoning="The query contains symptoms or language that may require urgent care.",
            )
        if any(term in text for term in ("systematic review", "guideline", "meta-analysis", "trial")):
            return IntentDecision(intent="research", reasoning="The query asks for evidence-level detail.")
        return IntentDecision(intent="educational", reasoning="No emergency language detected.")


def emergency_response(
    *,
    query_text: str = "",
    patient_context: Any = None,
    location_context: dict[str, Any] | None = None,
) -> str:
    numbers = _emergency_numbers(location_context or {})
    profile_note = _profile_note(patient_context)
    symptom_note = " Your symptoms may be serious."
    lowered = query_text.lower()
    if "chest pain" in lowered and any(term in lowered for term in ("breath", "breathing", "breathe")):
        symptom_note = (
            " Chest pain with breathing difficulty can be a medical emergency and needs immediate evaluation."
        )

    return (
        f"I am concerned.{symptom_note}\n\n"
        f"Please call ambulance emergency help now: {numbers}.\n\n"
        "Do not drive yourself. Sit upright, loosen tight clothing, and ask someone nearby "
        "to stay with you until help arrives. If a doctor has prescribed emergency medicine "
        "for situations like this, use it exactly as prescribed. "
        f"{profile_note}"
        "I cannot diagnose or provide emergency care through chat, so please get urgent in-person help now."
    )


def _emergency_numbers(location_context: dict[str, Any]) -> str:
    country = str(location_context.get("country_code") or "").strip().upper()
    timezone = str(location_context.get("timezone") or "").lower()
    locale = str(location_context.get("locale") or "").upper()

    if not country:
        if "KOLKATA" in timezone or "CALCUTTA" in timezone or locale.endswith("-IN"):
            country = "IN"

    emergency_by_country = {
        "IN": "India ambulance 108, or 112",
        "US": "United States 911",
        "CA": "Canada 911",
        "GB": "United Kingdom 999 or 112",
        "AU": "Australia 000",
        "NZ": "New Zealand 111",
        "AE": "United Arab Emirates 998 for ambulance or 999 for police",
        "SG": "Singapore 995",
        "EU": "112",
    }
    return emergency_by_country.get(country, "India ambulance 108, or 112")


def _profile_note(patient_context: Any) -> str:
    if patient_context is None:
        return ""
    if hasattr(patient_context, "model_dump"):
        data = patient_context.model_dump()
    elif isinstance(patient_context, dict):
        data = patient_context
    else:
        return ""

    details = []
    if data.get("age") is not None:
        details.append(f"age {data['age']}")
    if data.get("sex"):
        details.append(f"sex: {data['sex']}")
    conditions = data.get("conditions") or []
    medications = data.get("medications") or []
    allergies = data.get("allergies") or []
    if conditions:
        details.append("conditions: " + ", ".join(str(item) for item in conditions))
    if medications:
        details.append("medications: " + ", ".join(str(item) for item in medications))
    if allergies:
        details.append("allergies: " + ", ".join(str(item) for item in allergies))
    if data.get("additional_notes"):
        details.append("additional notes: " + str(data["additional_notes"]))
    if not details:
        return ""
    return "Tell the emergency team your profile details: " + "; ".join(details) + ". "
