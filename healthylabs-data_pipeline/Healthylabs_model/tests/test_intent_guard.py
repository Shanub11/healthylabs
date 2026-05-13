from healthylabs_inference.orchestrator.intent_guard import IntentGuard


def test_emergency_heuristic_short_circuits_high_risk_language():
    decision = IntentGuard().classify("I have chest pain and cannot breathe")

    assert decision.intent == "emergency"


def test_general_question_defaults_to_educational():
    decision = IntentGuard().classify("What is pneumonia?")

    assert decision.intent == "educational"
