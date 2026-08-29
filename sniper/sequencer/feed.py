from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import websockets


@dataclass(frozen=True, slots=True)
class FeedObservation:
    sequence_number: int | None
    received_ns: int
    message_count: int


class SequencerFeed:
    """Health/trigger observer for the Arbitrum Nitro broadcast feed.

    This intentionally does not decode compressed L2 messages or submit transactions. Robinhood's
    endpoint uses the Nitro feed, not Ethereum `eth_subscribe`. Execution always has RPC/WebSocket
    fallbacks because the feed is provisional and may disconnect.
    """

    def __init__(self, url: str) -> None:
        self.url = url
        self.connected = False
        self.last_message_ns: int | None = None
        self.last_error: str | None = None

    async def probe(self, timeout_seconds: float = 6.0) -> None:
        async with asyncio.timeout(timeout_seconds):
            async with websockets.connect(
                self.url,
                ping_interval=15,
                ping_timeout=15,
                open_timeout=timeout_seconds,
                max_size=16 * 1024 * 1024,
            ):
                return

    async def observations(self) -> AsyncIterator[FeedObservation]:
        backoff = 0.5
        while True:
            try:
                async with websockets.connect(
                    self.url,
                    ping_interval=15,
                    ping_timeout=15,
                    open_timeout=5,
                    max_size=16 * 1024 * 1024,
                ) as socket:
                    self.connected = True
                    self.last_error = None
                    backoff = 0.5
                    async for raw in socket:
                        self.last_message_ns = time.perf_counter_ns()
                        body = json.loads(raw)
                        messages = body.get("messages", []) if isinstance(body, dict) else []
                        sequence = _sequence_number(messages)
                        yield FeedObservation(sequence, self.last_message_ns, len(messages))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.connected = False
                self.last_error = type(exc).__name__
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 15)


def _sequence_number(messages: Any) -> int | None:
    if not isinstance(messages, list) or not messages:
        return None
    first = messages[0]
    if not isinstance(first, dict):
        return None
    value = first.get("sequenceNumber")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return None
    return None
