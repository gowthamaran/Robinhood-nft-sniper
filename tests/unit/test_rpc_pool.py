from typing import Any

import pytest

from sniper.rpc.client import RPCClient, RPCError, RPCPool


@pytest.mark.asyncio
async def test_rpc_pool_failover(monkeypatch) -> None:
    async def fake_call(self: RPCClient, method: str, params: list[Any] | None = None) -> Any:
        if self.url.endswith("one"):
            raise RPCError("offline")
        if method == "eth_chainId":
            return hex(46630)
        if method == "eth_blockNumber":
            return hex(123)
        return "ok"

    monkeypatch.setattr(RPCClient, "call", fake_call)
    pool = RPCPool(["https://rpc.test/one", "https://rpc.test/two"], 46630)
    await pool.validate()
    assert await pool.call("eth_test") == "ok"


@pytest.mark.asyncio
async def test_wrong_chain_makes_pool_unhealthy(monkeypatch) -> None:
    async def fake_call(self: RPCClient, method: str, params: list[Any] | None = None) -> str:
        return hex(1 if method == "eth_chainId" else 123)

    monkeypatch.setattr(RPCClient, "call", fake_call)
    pool = RPCPool(["https://rpc.test/wrong"], 46630)
    with pytest.raises(RPCError, match="No configured RPC"):
        await pool.validate()
