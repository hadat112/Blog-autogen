import responses
import pytest

from app.integrations.ai.openai_compatible import OpenAICompatibleAIClient
from app.integrations.ai.ninerouter import NineRouterAI


def test_deprecated_ai_name_remains_compatible():
    assert NineRouterAI is OpenAICompatibleAIClient


@responses.activate
def test_new_chat_policy_makes_one_attempt_without_fallback():
    client = OpenAICompatibleAIClient(
        "key", "primary", "image", base_url="https://ai.test/v1", fallback_text_model="fallback"
    )
    responses.add(responses.POST, "https://ai.test/v1/chat/completions", json={"error": "rate limited"}, status=429)
    with pytest.raises(Exception):
        client.chat([{"role": "user", "content": "hello"}])
    assert len(responses.calls) == 1
    assert b'"model": "primary"' in responses.calls[0].request.body


@responses.activate
def test_chat_returns_tool_calls_without_requiring_text():
    client = OpenAICompatibleAIClient("key", "model", "image", base_url="https://ai.test/v1")
    responses.add(responses.POST, "https://ai.test/v1/chat/completions", json={"choices": [{"message": {"content": None, "tool_calls": [{"id": "1"}]}}]}, status=200)
    assert client.chat([{"role": "user", "content": "hello"}], tools=[])["tool_calls"][0]["id"] == "1"
