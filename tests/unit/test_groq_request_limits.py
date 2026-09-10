from app.services import ai_service


def test_public_chat_payload_disables_unnecessary_qwen_reasoning():
    payload = ai_service._chat_payload("question", "context", [], "pt")

    assert payload["reasoning_format"] == "hidden"
    assert payload["reasoning_effort"] == "none"
    assert payload["max_completion_tokens"] == 800
