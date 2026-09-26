import pytest

from app.domain.text_story_validation import assemble_story, validate_stage
from app.integrations.ai.openai_compatible import AITextResult


def result(content, finish_reason="stop"):
    return AITextResult(content, "model", finish_reason, {})


def test_visible_but_truncated_response_is_invalid():
    with pytest.raises(ValueError, match="incomplete"):
        validate_stage("rewrite", result("word " * 600, "length"))


def test_rewrite_word_count_and_sentence_end_are_checked():
    with pytest.raises(ValueError, match="550"):
        validate_stage("rewrite", result("word " * 548 + "End."))
    with pytest.raises(ValueError, match="sentence"):
        validate_stage("rewrite", result("word " * 599 + "unfinished"))
    assert validate_stage("rewrite", result("word " * 599 + "End."))


def test_continuation_rejects_copied_opening_and_short_or_incomplete_story():
    rewrite = "The room fell silent. Everyone watched the door."
    with pytest.raises(ValueError, match="repeat"):
        validate_stage("enhance", result(rewrite + " " + "word " * 3100 + "End."), rewrite)
    with pytest.raises(ValueError, match="3,000"):
        validate_stage("enhance", result("word " * 2998 + "End."), rewrite)
    with pytest.raises(ValueError, match="sentence"):
        validate_stage("enhance", result("word " * 3100 + "unfinished"), rewrite)


def test_assembly_keeps_rewrite_once_and_caption_exact():
    rewrite = "First sentence. Second sentence."
    content, caption = assemble_story(rewrite, "The end.")
    assert content == "First sentence. Second sentence.\n\nThe end."
    assert content.startswith(caption)
    assert caption == rewrite


def test_caption_stops_at_sentence_boundary_in_word_window():
    rewrite = ("One two three four five six seven eight nine ten. " * 8).strip()
    content, caption = assemble_story(rewrite, "The end.")
    assert 45 <= len(caption.split()) <= 70
    assert caption.endswith(".")
    assert content.startswith(caption)
