import json

import pytest

from app.domain.rewrite_engine import RewriteEngine


class FakeAI:
    def __init__(self):
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append(messages)
        if "Return JSON only" in messages[-1]["content"]:
            return {"content": json.dumps({"title": "New title", "caption": "First rewrite"})}
        return {"content": "First rewrite" if len(self.calls) == 1 else "Second rewrite"}


def test_rewrite_keeps_only_current_original_chunk_and_prior_assistant_output():
    ai = FakeAI()
    source = "original-one\n\noriginal-two"
    result = RewriteEngine(ai, chunk_size=12).rewrite("Old", source, "Italian")
    assert result["caption"] == "First rewrite"
    second_messages = ai.calls[1]
    assert any(message["role"] == "assistant" and message["content"] == "First rewrite" for message in second_messages)
    assert "original-one" not in second_messages[-1]["content"]
    assert "original-two" in second_messages[-1]["content"]
    final_roles = [message["role"] for message in ai.calls[-1]]
    assert final_roles == ["system", "assistant", "user", "assistant", "user"]


def test_rewrite_rejects_caption_that_is_not_exact_prefix():
    class BadAI(FakeAI):
        def chat(self, messages, **kwargs):
            if "Return JSON only" in messages[-1]["content"]:
                return {"content": '{"title":"New","caption":"not copied"}'}
            return {"content": "Story opening"}

    with pytest.raises(ValueError, match="exact prefix"):
        RewriteEngine(BadAI()).rewrite("Old", "source", "English")
