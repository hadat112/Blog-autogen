def normalize_language(language: str) -> str:
    lang = (language or "").strip().lower()
    aliases = {
        "uk": "uk",
        "ukrainian": "uk",
        "ukraina": "uk",
        "en": "en",
        "english": "en",
        "vi": "vi",
        "vietnamese": "vi",
        "hr": "hr",
        "croatian": "hr",
        "ro": "ro",
        "romanian": "ro",
        "it": "it",
        "italian": "it",
        "pl": "pl",
        "polish": "pl",
    }
    if lang in aliases:
        return aliases[lang]
    raise ValueError("Unsupported language. Use Ukrainian, Vietnamese, English, Croatian, Romanian, Italian, or Polish.")
