import json
from decimal import Decimal
from typing import Any

import pytest
from eth_account import Account
from pydantic import HttpUrl

import sniper.mint.engine as engine_module
from sniper.config import (
    AppConfig,
    LimitSettings,
    RPCSettings,
    TargetSettings,
    WalletSettings,
)
from sniper.mint.engine import MintEngine
from sniper.models import ExecutionMode, MintState
from sniper.rpc.client import EndpointHealth, RPCPool
from sniper.storage import StateStore

ABI = [
    {
        "type": "function",
        "name": "mint",
        "stateMutability": "payable",
        "inputs": [{"name": "quantity", "type": "uint256"}],
        "outputs": [],
    }
]


@pytest.mark.asyncio
async def test_full_dry_run_pipeline_never_signs_or_broadcasts(tmp_path, monkeypatch) -> None:
    abi_path = tmp_path / "mint-abi.json"
    abi_path.write_text(json.dumps(ABI), encoding="utf-8")
    account = Account.create()
    contract = "0x0000000000000000000000000000000000000001"
    config = AppConfig(
        network="testnet",
        chain_id=46630,
        rpc=RPCSettings(primary=HttpUrl("https://rpc.test")),
        wallet=WalletSettings(address=account.address, keystore_path="unused"),
        target=TargetSettings(
            contract=contract,
            abi_path=str(abi_path),
            function="mint",
            arguments=[1],
            quantity=1,
            transaction_value_eth=Decimal("0.001"),
        ),
        limits=LimitSettings(
            max_price_per_nft_eth=Decimal("0.002"),
            max_network_fee_eth=Decimal("0.01"),
            max_total_spend_eth=Decimal("0.02"),
            balance_buffer_eth=Decimal("0.001"),
        ),
        mode=ExecutionMode.AUTO,
        sequencer_feed_enabled=False,
    )

    async def fake_validate(self: RPCPool) -> list[EndpointHealth]:
        return [
            EndpointHealth(
                "https://rpc.test",
                latency_ms=1,
                block_number=10,
                successes=1,
                validated_chain=True,
            )
        ]

    async def fake_call(self: RPCPool, method: str, params: list[Any] | None = None) -> Any:
        responses: dict[str, Any] = {
            "eth_chainId": hex(46630),
            "eth_getTransactionCount": hex(0),
            "eth_gasPrice": hex(1_000_000_000),
            "eth_getBalance": hex(10**18),
            "eth_call": "0x",
            "eth_estimateGas": hex(100_000),
        }
        return responses[method]

    async def fake_analysis(*args: Any, **kwargs: Any) -> dict[str, object]:
        return {"address": contract, "standard": "ERC-721-like"}

    broadcast_called = False

    async def forbidden_broadcast(self: RPCPool, raw_transaction: str) -> str:
        nonlocal broadcast_called
        broadcast_called = True
        raise AssertionError("dry run must never broadcast")

    monkeypatch.setattr(RPCPool, "validate", fake_validate)
    monkeypatch.setattr(RPCPool, "call", fake_call)
    monkeypatch.setattr(RPCPool, "broadcast_same_raw", forbidden_broadcast)
    monkeypatch.setattr(engine_module, "analyze_contract", fake_analysis)

    engine = MintEngine(config, account, StateStore(tmp_path / "state-root"))
    await engine.prepare()
    await engine.wait_for_trigger(stop_after=1)
    result = await engine.execute(dry_run=True)
    await engine.close()

    assert result.state == MintState.SKIPPED
    assert result.message == "Dry run: safe to submit"
    assert result.tx_hash is None
    assert not broadcast_called
    assert result.spend is not None
    assert result.timings_ms["simulation"] >= 0
