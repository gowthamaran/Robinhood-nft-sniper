from __future__ import annotations

import logging
import re
from collections.abc import Iterable

PRIVATE_KEY = re.compile(r"(?i)(?:0x)?[0-9a-f]{64}")
TELEGRAM_TOKEN = re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b")
URL_CREDENTIAL = re.compile(
    r"(?i)(https?|wss?)://([^/@\s]+)@|([?&](?:api[_-]?key|token|key)=)[^&\s]+"
)
PROVIDER_PATH_KEY = re.compile(r"(?i)(/(?:v2|v3)/)[A-Za-z0-9_-]{16,}")


def redact(value: object, extra_secrets: Iterable[str] = ()) -> str:
    text = str(value)
    for secret in extra_secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    text = PRIVATE_KEY.sub("[REDACTED_PRIVATE_KEY]", text)
    text = TELEGRAM_TOKEN.sub("[REDACTED_TELEGRAM_TOKEN]", text)
    text = URL_CREDENTIAL.sub(
        lambda match: (
            f"{match.group(1)}://[REDACTED]@" if match.group(1) else f"{match.group(3)}[REDACTED]"
        ),
        text,
    )
    return PROVIDER_PATH_KEY.sub(r"\1[REDACTED]", text)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.msg)
        if record.args:
            record.args = tuple(redact(item) for item in record.args)
        return True


def abbreviated(value: str, left: int = 6, right: int = 4) -> str:
    return value if len(value) <= left + right else f"{value[:left]}...{value[-right:]}"
