from healthylabs_inference.orchestrator.intent_guard import IntentGuard


class EducationalLLM:
    def generate_json(self, *args, **kwargs):
        return {"intent": "research", "reasoning": "The user asks mechanistic research."}


def test_llm_can_override_emergency_keyword_for_research_query():
    decision = IntentGuard(EducationalLLM()).classify(
        "What is the mechanism of seizure in status epilepticus?"
    )

    assert decision.intent == "research"
    assert decision.source == "llm"
