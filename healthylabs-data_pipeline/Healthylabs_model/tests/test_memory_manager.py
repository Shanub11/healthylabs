import pytest

pytest.importorskip("pydantic")

from healthylabs_inference.api.request_models import ChatMessage, QueryRequest
from healthylabs_inference.core.config import Settings
from healthylabs_inference.orchestrator.memory import SessionMemoryManager


class MemoryLLM:
    def __init__(self):
        self.prompt = ""

    def generate_json(self, prompt, **kwargs):
        self.prompt = prompt
        return {
            "session_summary": "User asked about headache after pneumonia antibiotics.",
            "pinned_medical_facts": {"symptoms": ["headache"], "conditions": ["pneumonia"]},
            "open_questions": ["Which antibiotic is being taken?"],
            "safety_notes": ["Seek care for severe or worsening symptoms."],
        }


class FailingLLM:
    def generate_json(self, prompt, **kwargs):
        raise RuntimeError("down")


def test_memory_manager_updates_structured_memory_and_uses_recent_turn_window():
    llm = MemoryLLM()
    request = QueryRequest(
        query_text="Could it be the antibiotic?",
        session_summary="prior summary",
        chat_history=[
            ChatMessage(role="user", content="old"),
            ChatMessage(role="assistant", content="middle"),
            ChatMessage(role="user", content="new"),
        ],
    )

    update = SessionMemoryManager(Settings(memory_recent_turn_window=2), llm).update(
        request=request,
        answer="Possible side effect; check with clinician.",
        safety_flags=["low_retrieval_confidence"],
    )

    assert update.source == "llm"
    assert update.pinned_medical_facts["symptoms"] == ["headache"]
    assert '"old"' not in llm.prompt
    assert "middle" in llm.prompt
    assert "new" in llm.prompt


def test_memory_manager_falls_back_to_frontend_memory_on_llm_failure():
    request = QueryRequest(
        query_text="Could it be the antibiotic?",
        session_summary="keep me",
        pinned_medical_facts={"allergies": ["penicillin"]},
        open_questions=["Which antibiotic?"],
        safety_notes=["Check allergy."],
    )

    update = SessionMemoryManager(Settings(), FailingLLM()).update(
        request=request,
        answer="answer",
        safety_flags=[],
    )

    assert update.source == "fallback"
    assert update.session_summary == "keep me"
    assert update.pinned_medical_facts == {"allergies": ["penicillin"]}
    assert update.open_questions == ["Which antibiotic?"]
