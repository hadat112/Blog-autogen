import requests


def fetch_telegram_updates(token, offset=None, timeout=30):
    """
    Fetches updates via Telegram Bot API.
    """
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    payload = {"timeout": timeout}
    if offset is not None:
        payload["offset"] = offset
    response = requests.get(url, params=payload, timeout=timeout + 5)
    response.raise_for_status()
    return response.json()


def send_telegram_msg(token, chat_id, message):
    """
    Sends a message via Telegram Bot API.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()
