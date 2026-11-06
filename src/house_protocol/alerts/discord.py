# DM sender

import logging
import time

import requests

logger = logging.getLogger(__name__)

API_URL = "https://discord.com/api/v10"
MAX_LEN = 2000
USER_AGENT = "HouseProtocol (Media Monitor bot, 0.1)"


def split_message(text: str, limit: int = MAX_LEN) -> list[str]:
    # splits message into chunks

    chunks: list[str] = []
    current = ""

    for line in text.splitlines():
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if current and len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


def _post(session: requests.Session, url: str, token: str, payload: dict) -> dict:
    headers = {"Authorization": f"Bot {token}", "User-Agent": USER_AGENT}

    for attempt in range(2):
        resp = session.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 429 and attempt == 0:
            wait = resp.json().get("retry_after", 1)
            logger.warning("discord rate limited, waiting %ss", wait)
            time.sleep(wait)

            continue

        if resp.status_code >= 400:
            raise RuntimeError(f"Discord API error {resp.status_code}: {resp.text[:200]}")

        return resp.json()

    raise RuntimeError("Discord API still rate limited after retry")


def send_dm(
    user_id: str,
    token: str,
    text: str,
    session: requests.Session | None = None,
) -> None:
    # DM text to a user, splitting it if its longer than allowed

    session = session or requests.Session()

    channel = _post(session, f"{API_URL}/users/@me/channels", token, {"recipient_id": str(user_id)})

    for chunk in split_message(text):
        _post(session, f"{API_URL}/channels/{channel['id']}/messages", token, {"content": chunk})
