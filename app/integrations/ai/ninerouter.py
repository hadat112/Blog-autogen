"""Deprecated compatibility imports for the former vendor-specific module name."""

from .openai_compatible import (
    AI_MAX_ATTEMPTS,
    CHUNKED_ARTICLE_THRESHOLD,
    CINEMATIC_NATURALISM_STYLE_PROMPT,
    DEFAULT_AI_REQUEST_TIMEOUT,
    DEFAULT_TRANSLATION_MAX_CONCURRENCY,
    DEFAULT_TRANSLATION_MODE,
    REQUIRED_ARTICLE_KEYS,
    REQUIRED_STORY_KEYS,
    TRANSLATION_CHUNK_SIZE,
    TRANSLATION_CONTEXT_PARAGRAPHS,
    TRANSLATION_MAX_RETRIES,
    TRANSLATION_MODES,
    TRANSLATION_PREFIX_RE,
    TRANSLATION_RETRY_DELAYS,
    TRANSLATION_TEMPERATURE,
    TRANSIENT_STATUS_CODES,
    OpenAICompatibleAIClient,
    _build_styled_image_prompt,
    _clean_translation_output,
    _extract_article_fields_locally,
    _extract_first_balanced_json_object,
    _format_seconds,
    _get_ai_request_timeout,
    _normalize_ai_request_timeout,
    _normalize_translation_chunk_size,
    _normalize_translation_max_concurrency,
    _normalize_translation_mode,
    _paragraphs,
    _parse_article_json,
    _parse_story_json,
    _split_text_chunks,
    _tail_paragraph_context,
    _word_count,
)


NineRouterAI = OpenAICompatibleAIClient

__all__ = ["NineRouterAI", "OpenAICompatibleAIClient"]
