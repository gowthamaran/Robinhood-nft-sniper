from __future__ import annotations

import asyncio
import itertools
import time
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from sniper.network.robinhood import validate_chain_id


class RPCError(RuntimeError):
    def __init__(self, message: str, code: int | None = None, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = data


@dataclass(slots=True)
class EndpointHealth:
    url: str
    latency_ms: float = float("inf")
    block_number: int = 0
    successes: int = 0
    failures: int = 0
    last_error: str | None = None
    updated_at: float = 0.0
    validated_chain: bool = False

    @property
    def reliability(self) -> float:
        total = self.successes + self.failures
        return self.successes / total if total else 0.0

    def score(self, freshest_block: int) -> float:
        if self.successes == 0:
            return float("inf")
        lag_penalty = max(0, freshest_block - self.block_number) * 1_000
        failure_penalty = (1 - self.reliability) * 2_000
        return self.latency_ms + lag_penalty + failure_penalty


class RPCClient:
    _ids = itertools.count(1)

    def __init__(self, url: str, timeout: float = 4.0) -> None:
        self.url = url
        self.timeout = timeout
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> RPCClient:
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def start(self) -> None:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(
                limit=20, ttl_dns_cache=300, enable_cleanup_closed=True
            )
            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def call(self, method: str, params: list[Any] | None = None) -> Any:
        await self.start()
        assert self._session is not None
        payload = {
            "jsonrpc": "2.0",
            "id": next(self._ids),
            "method": method,
            "params": params or [],
        }
        try:
            async with self._session.post(self.url, json=payload) as response:
                response.raise_for_status()
                body = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            raise RPCError(f"RPC transport error: {type(exc).__name__}") from exc
        if "error" in body:
            error = body["error"]
            raise RPCError(error.get("message", "RPC error"), error.get("code"), error.get("data"))
        if "result" not in body:
            raise RPCError("Malformed JSON-RPC response")
        return body["result"]


@dataclass(slots=True)
class RPCPool:
    urls: list[str]
    expected_chain_id: int
    timeout: float = 4.0
    clients: list[RPCClient] = field(init=False)
    health: dict[str, EndpointHealth] = field(init=False)

    def __post_init__(self) -> None:
        unique_urls = list(dict.fromkeys(self.urls))
        if not unique_urls:
            raise ValueError("At least one RPC URL is required")
        self.urls = unique_urls
        self.clients = [RPCClient(url, self.timeout) for url in unique_urls]
        self.health = {url: EndpointHealth(url) for url in unique_urls}

    async def close(self) -> None:
        await asyncio.gather(*(client.close() for client in self.clients))

    async def validate(self) -> list[EndpointHealth]:
        results = await asyncio.gather(
            *(self._probe(client, validate=True) for client in self.clients), return_exceptions=True
        )
        healthy = [
            item
            for item in results
            if isinstance(item, EndpointHealth)
            and item.successes > 0
            and item.last_error is None
            and item.validated_chain
        ]
        if not healthy:
            raise RPCError("No configured RPC passed chain and freshness validation")
        return sorted(healthy, key=lambda item: item.score(max(x.block_number for x in healthy)))

    async def benchmark(self, rounds: int = 3) -> list[EndpointHealth]:
        for _ in range(rounds):
            await asyncio.gather(*(self._probe(client, validate=True) for client in self.clients))
        freshest = max((item.block_number for item in self.health.values()), default=0)
        return sorted(self.health.values(), key=lambda item: item.score(freshest))

    async def _probe(self, client: RPCClient, validate: bool) -> EndpointHealth:
        health = self.health[client.url]
        started = time.perf_counter()
        try:
            chain_hex, block_hex = await asyncio.gather(
                client.call("eth_chainId"), client.call("eth_blockNumber")
            )
            chain_id = int(chain_hex, 16)
            if validate:
                validate_chain_id(chain_id, self.expected_chain_id)
                health.validated_chain = True
            health.block_number = int(block_hex, 16)
            elapsed = (time.perf_counter() - started) * 1_000
            health.latency_ms = (
                elapsed if health.successes == 0 else health.latency_ms * 0.7 + elapsed * 0.3
            )
            health.successes += 1
            health.last_error = None
        except Exception as exc:
            health.failures += 1
            health.last_error = str(exc)
            if isinstance(exc, ValueError) and "chain" in str(exc).lower():
                health.validated_chain = False
        health.updated_at = time.time()
        return health

    def ranked_clients(self) -> list[RPCClient]:
        freshest = max((item.block_number for item in self.health.values()), default=0)
        eligible = [client for client in self.clients if self.health[client.url].validated_chain]
        return sorted(eligible, key=lambda client: self.health[client.url].score(freshest))

    async def call(self, method: str, params: list[Any] | None = None) -> Any:
        errors: list[str] = []
        for client in self.ranked_clients():
            try:
                return await client.call(method, params)
            except RPCError as exc:
                self.health[client.url].failures += 1
                self.health[client.url].last_error = str(exc)
                errors.append(f"{client.url}: {exc}")
        raise RPCError(f"All RPC endpoints failed for {method}: {'; '.join(errors)}")

    async def broadcast_same_raw(self, raw_transaction: str) -> str:
        """Propagate one signed transaction to at most two healthy endpoints."""
        clients = self.ranked_clients()[:2]
        tasks = [client.call("eth_sendRawTransaction", [raw_transaction]) for client in clients]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, str):
                return result
        messages = [str(item) for item in results]
        already_known = any(
            token in message.lower()
            for message in messages
            for token in ("already known", "known transaction", "nonce too low")
        )
        if already_known:
            from eth_utils.crypto import keccak

            return "0x" + keccak(bytes.fromhex(raw_transaction.removeprefix("0x"))).hex()
        raise RPCError(f"Broadcast failed: {'; '.join(messages)}")
