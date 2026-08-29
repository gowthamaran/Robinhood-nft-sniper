from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import websockets


async def probe_new_heads(url: str, timeout_seconds: float = 6.0) -> str:
    async with asyncio.timeout(timeout_seconds):
        async with websockets.connect(
            url,
            ping_interval=15,
            ping_timeout=15,
            open_timeout=timeout_seconds,
            max_size=2**20,
        ) as socket:
            await socket.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_subscribe",
                        "params": ["newHeads"],
                    }
                )
            )
            acknowledgement = json.loads(await socket.recv())
            subscription = acknowledgement.get("result")
            if not isinstance(subscription, str):
                raise RuntimeError(
                    f"WebSocket subscription rejected: {acknowledgement.get('error')}"
                )
            return subscription


async def new_heads(url: str) -> AsyncIterator[dict[str, object]]:
    backoff = 0.5
    while True:
        try:
            async with websockets.connect(
                url, ping_interval=15, ping_timeout=15, open_timeout=5, max_size=2**20
            ) as socket:
                await socket.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "eth_subscribe",
                            "params": ["newHeads"],
                        }
                    )
                )
                acknowledgement = json.loads(await socket.recv())
                if "error" in acknowledgement:
                    raise RuntimeError(str(acknowledgement["error"]))
                backoff = 0.5
                async for message in socket:
                    body = json.loads(message)
                    result = body.get("params", {}).get("result")
                    if isinstance(result, dict):
                        yield result
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 15)
