"""Rolling session-memory compression for stateless chatbot clients."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from healthylabs_inference.api.request_models import QueryRequest
from healthylabs_inference.core.config import Settings
from healthylabs_inference.core.llm_client import GeminiClient
from healthylabs_inference.orchestrator.prompts import SESSION_MEMORY_PROMPT, object_to_json


@dataclass(frozen=True, slots=True)
class SessionMemoryUpdate:
    """Compressed session memory returned to the frontend for the next turn."""

    session_summary: str | None = None
    pinned_medical_facts: dict[str, Any] = field(default_factory=dict)
    open_questions: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)
    source: str = "fallback"


class SessionMemoryManager:
    """Maintains hybrid rolling memory without storing sessions server-side."""

    def __init__(self, settings: Settings, llm_client: GeminiClient | None = None):
        self._settings = settings
        self._llm = llm_client

    def update(
        self,
        *,
        request: QueryRequest,
        answer: str,
        safety_flags: list[str],
    ) -> SessionMemoryUpdate:
        fallback = self._fallback_from_request(request)
        if self._llm is None:
            return fallback
        recent_chat = [
            message.model_dump() for message in request.chat_history[-self._settings.memory_recent_turn_window :]
        ]
        prompt = SESSION_MEMORY_PROMPT.format(
            prior_memory_json=object_to_json(
                {
                    "session_summary": request.session_summary,
                    "pinned_medical_facts": request.pinned_medical_facts,
                    "open_questions": request.open_questions,
                    "safety_notes": request.safety_notes,
                }
            ),
            query_text=request.query_text,
            answer_text=answer[:2_500],
            recent_chat_json=object_to_json(recent_chat),
            patient_context_json=object_to_json(request.patient_context or {}),
            safety_flags_json=object_to_json(safety_flags),
            max_summary_words=self._settings.memory_summary_max_words,
        )
        try:
            parsed = self._llm.generate_json(prompt, temperature=0.0, max_output_tokens=900)
        except (ValueError, TypeError, RuntimeError):
            return fallback
        return SessionMemoryUpdate(
            session_summary=_optional_str(parsed.get("session_summary")) or fallback.session_summary,
            pinned_medical_facts=_dict_or_default(
                parsed.get("pinned_medical_facts"), fallback.pinned_medical_facts
            ),
            open_questions=_string_list(parsed.get("open_questions"), fallback.open_questions),
            safety_notes=_string_list(parsed.get("safety_notes"), fallback.safety_notes),
            source="llm",
        )

    @staticmethod
    def _fallback_from_request(request: QueryRequest) -> SessionMemoryUpdate:
        return SessionMemoryUpdate(
            session_summary=request.session_summary,
            pinned_medical_facts=dict(request.pinned_medical_facts),
            open_questions=list(request.open_questions),
            safety_notes=list(request.safety_notes),
            source="fallback",
        )


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _dict_or_default(value: Any, default: dict[str, Any]) -> dict[str, Any]:
    return value if isinstance(value, dict) else default


def _string_list(value: Any, default: list[str]) -> list[str]:
    if not isinstance(value, list):
        return default
    return [str(item) for item in value if str(item).strip()]
