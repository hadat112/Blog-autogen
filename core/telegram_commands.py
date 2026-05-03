from core.run_options import parse_run_tokens


def handle_telegram_message(text: str, config: dict, job_runner) -> str:
    message = (text or "").strip()
    if not message.startswith("/run"):
        return "Unsupported command. Use /run ..."

    tokens = message.split()[1:]
    try:
        options = parse_run_tokens(tokens)
        options.resolve_enable_image(config.get("enable_image_generation", True))
    except Exception as e:
        return f"Error: {e}"

    return "Run accepted. Starting..."


def parse_run_options_from_message(text: str, config: dict):
    message = (text or "").strip()
    if not message.startswith("/run"):
        raise ValueError("Unsupported command. Use /run ...")

    tokens = message.split()[1:]
    options = parse_run_tokens(tokens)
    options.resolve_enable_image(config.get("enable_image_generation", True))
    return options