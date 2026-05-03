def normalize_language(language: str) -> str:
    lang = (language or "").strip().lower()
    aliases = {
        "uk": "uk",
        "ukrainian": "uk",
        "ukraina": "uk",
        "en": "en",
        "english": "en",
    }
    if lang in aliases:
        return aliases[lang]
    raise ValueError("Unsupported language. Use Ukraina/Ukrainian, Vietnamese, or English.")
