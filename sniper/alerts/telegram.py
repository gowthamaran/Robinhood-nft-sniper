from __future__ import annotations

import aiohttp

from sniper.security.redaction import redact


async def notify(token: str, chat_id: str, message: str) -> None:
    """Send sanitized text only; Telegram never accepts commands in V1."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            url,
            json={
                "chat_id": chat_id,
                "text": redact(message, [token]),
                "disable_web_page_preview": True,
            },
        ) as response:
            response.raise_for_status()
