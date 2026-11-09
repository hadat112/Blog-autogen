from app.domain.translation_settings import resolve_translation_chunk_size
from app.domain.settings_manager import SettingsManager
from app.integrations.ai.openai_compatible import OpenAICompatibleAIClient
from app.services.account_service import DEFAULT_AI_BASE_URL


def create_ai_client(account, settings=None):
    config = dict(account.config or {})
    app_settings = settings or SettingsManager().config
    return OpenAICompatibleAIClient(
        api_key=config.get("api_key"),
        text_model=config.get("text_model"),
        image_model=config.get("image_model"),
        fallback_text_model=config.get("fallback_text_model"),
        base_url=config.get("base_url") or DEFAULT_AI_BASE_URL,
        translation_mode=app_settings.get("translation_mode", "sequential"),
        translation_max_concurrency=app_settings.get("translation_max_concurrency", 2),
        ai_request_timeout=app_settings.get("ai_request_timeout", 300),
        translation_chunk_size=resolve_translation_chunk_size(config, app_settings),
        account_key=account.id,
        max_concurrency=config.get("max_concurrency", 2),
    )
