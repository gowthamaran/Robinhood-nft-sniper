from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from web3 import Web3

from sniper.config import AppConfig
from sniper.contract.analyzer import analyze_contract, encode_call, load_abi
from sniper.mint.limits import LimitViolation, SpendCheck, enforce_limits, eth_to_wei
from sniper.models import ExecutionMode, MintState
from sniper.network.robinhood import get_network, validate_chain_id
from sniper.opensea import OpenSeaClient, OpenSeaError
from sniper.rpc.client import RPCError, RPCPool
from sniper.rpc.websocket import new_heads
from sniper.sequencer.feed import SequencerFeed
from sniper.storage import StateStore


def as_hex(value: int) -> str:
    return hex(value)


def decode_revert(error: RPCError) -> str:
    message = str(error)
    markers = (
        "SaleNotActive",
        "MintClosed",
        "SoldOut",
        "WalletLimitExceeded",
        "InvalidProof",
        "InvalidSignature",
        "InsufficientPayment",
    )
    for marker in markers:
        if marker.lower() in message.lower():
            return marker
    return message[:180]


@dataclass(slots=True)
class ExecutionResult:
    state: MintState
    tx_hash: str | None = None
    receipt: dict[str, Any] | None = None
    spend: SpendCheck | None = None
    timings_ms: dict[str, float] = field(default_factory=dict)
    message: str = ""


class MintEngine:
    def __init__(self, config: AppConfig, account: LocalAccount, store: StateStore) -> None:
        self.config = config
        self.account = account
        self.store = store
        self.rpc = RPCPool(config.rpc.all_http(), config.chain_id, config.rpc.timeout_seconds)
        self.contract: ChecksumAddress = Web3.to_checksum_address(config.target.contract)
        self.opensea: OpenSeaClient | None = None
        if config.target.source == "opensea":
            assert config.target.opensea_api_key_path is not None
            self.abi: list[dict[str, Any]] = []
            self.calldata = "0x"
            self.value_wei = 0
            self.opensea = OpenSeaClient(Path(config.target.opensea_api_key_path))
        else:
            assert config.target.abi_path is not None
            assert config.target.function is not None
            self.abi = load_abi(config.target.abi_path)
            self.calldata = encode_call(
                self.contract, self.abi, config.target.function, config.target.arguments
            )
            self.value_wei = eth_to_wei(config.target.transaction_value_eth)
        self.run_id = store.create_run(account.address, self.contract)

    async def close(self) -> None:
        await self.rpc.close()
        if self.opensea is not None:
            await self.opensea.close()

    async def prepare(self, allow_rearm: bool = False) -> dict[str, object]:
        if self.store.already_broadcast(self.account.address, self.contract) and not allow_rearm:
            raise RuntimeError(
                "Duplicate guard: this wallet already broadcast for this target. "
                "Use explicit rearm."
            )
        healthy = await self.rpc.validate()
        if self.opensea is not None:
            assert self.config.target.opensea_slug is not None
            drop = await self.opensea.get_drop(self.config.target.opensea_slug)
            self._validate_opensea_chain(drop.chain)
            if drop.contract.lower() != self.config.target.contract.lower():
                raise OpenSeaError("OpenSea drop contract changed since setup; run setup again")
            code = await self.rpc.call("eth_getCode", [drop.contract, "latest"])
            if code in {"0x", "0x0"}:
                raise OpenSeaError("OpenSea drop contract has no code on Robinhood Chain")
            analysis: dict[str, object] = {
                "address": drop.contract,
                "source": "OpenSea Drops API",
            }
        else:
            assert self.config.target.function is not None
            analysis = await analyze_contract(
                self.rpc,
                self.contract,
                self.abi,
                self.config.target.function,
                self.config.target.arguments,
            )
        chain_id = int(await self.rpc.call("eth_chainId"), 16)
        validate_chain_id(chain_id, self.config.chain_id)
        self.store.transition(self.run_id, MintState.ARMED)
        return {"analysis": analysis, "rpc": healthy}

    def _validate_opensea_chain(self, chain: str) -> None:
        if self.config.network != "mainnet" or chain != "robinhood":
            raise OpenSeaError(
                f"OpenSea returned chain '{chain or 'unknown'}'; this target requires "
                "Robinhood Chain mainnet"
            )

    async def _refresh_opensea_transaction(self) -> None:
        assert self.opensea is not None
        assert self.config.target.opensea_slug is not None
        transaction = await self.opensea.build_mint(
            self.config.target.opensea_slug,
            self.account.address,
            self.config.target.quantity,
        )
        self._validate_opensea_chain(transaction.chain)
        code = await self.rpc.call("eth_getCode", [transaction.to, "latest"])
        if code in {"0x", "0x0"}:
            raise OpenSeaError("OpenSea transaction target is not a deployed contract")
        self.contract = Web3.to_checksum_address(transaction.to)
        self.calldata = transaction.data
        self.value_wei = transaction.value_wei

    def _call_object(self) -> dict[str, str]:
        return {
            "from": self.account.address,
            "to": self.contract,
            "data": self.calldata,
            "value": as_hex(self.value_wei),
        }

    async def simulate(self) -> str:
        return str(await self.rpc.call("eth_call", [self._call_object(), "pending"]))

    async def wait_for_trigger(self, stop_after: float | None = None) -> None:
        if self.opensea is not None:
            await self._wait_for_opensea_trigger(stop_after)
            return
        started = time.monotonic()
        interval = self.config.target.poll_interval_ms / 1_000
        wake = asyncio.Event()

        async def websocket_waker() -> None:
            assert self.config.rpc.websocket is not None
            async for _ in new_heads(self.config.rpc.websocket):
                wake.set()

        async def feed_waker() -> None:
            network = get_network(self.config.network)
            async for _ in SequencerFeed(network.sequencer_feed).observations():
                wake.set()

        watchers: list[asyncio.Task[None]] = []
        if self.config.rpc.websocket:
            watchers.append(asyncio.create_task(websocket_waker()))
        if self.config.sequencer_feed_enabled:
            watchers.append(asyncio.create_task(feed_waker()))
        try:
            while True:
                attempt_started = time.monotonic()
                try:
                    await self.simulate()
                    return
                except RPCError:
                    if stop_after is not None and time.monotonic() - started > stop_after:
                        raise TimeoutError(
                            "No successful mint simulation before watch timeout"
                        ) from None
                    remaining = max(0.01, interval - (time.monotonic() - attempt_started))
                    try:
                        await asyncio.wait_for(wake.wait(), timeout=remaining)
                    except TimeoutError:
                        pass
                    wake.clear()
        finally:
            for task in watchers:
                task.cancel()
            await asyncio.gather(*watchers, return_exceptions=True)

    async def _wait_for_opensea_trigger(self, stop_after: float | None) -> None:
        assert self.opensea is not None
        assert self.config.target.opensea_slug is not None
        started = time.monotonic()
        early_mint_attempts = 0
        while True:
            if stop_after is not None and time.monotonic() - started > stop_after:
                raise TimeoutError("OpenSea drop did not become mintable before watch timeout")
            drop = await self.opensea.get_drop(self.config.target.opensea_slug)
            self._validate_opensea_chain(drop.chain)
            now = datetime.now(UTC)
            stage_due = drop.next_start is not None and drop.next_start <= now
            if drop.active or (stage_due and early_mint_attempts < 10):
                try:
                    await self._refresh_opensea_transaction()
                except OpenSeaError as exc:
                    if exc.status == 422:
                        raise
                    if exc.status == 409:
                        early_mint_attempts += 1
                        await asyncio.sleep(0.25)
                        continue
                    raise
                while True:
                    try:
                        await self.simulate()
                        return
                    except RPCError:
                        if stop_after is not None and time.monotonic() - started > stop_after:
                            raise TimeoutError(
                                "OpenSea mint transaction did not simulate before watch timeout"
                            ) from None
                        await asyncio.sleep(self.config.target.poll_interval_ms / 1_000)
            seconds_to_start = (
                (drop.next_start - now).total_seconds() if drop.next_start is not None else 6.0
            )
            if stage_due and early_mint_attempts >= 10:
                seconds_to_start = 6.0
            await asyncio.sleep(max(0.1, min(30.0, seconds_to_start)))

    async def execute(self, *, dry_run: bool = False, confirmed: bool = False) -> ExecutionResult:
        timings: dict[str, float] = {}
        trigger_ns = time.perf_counter_ns()
        self.store.transition(self.run_id, MintState.TRIGGERED)
        self.store.transition(self.run_id, MintState.SIMULATING)

        refresh_ns = time.perf_counter_ns()
        nonce_hex, gas_price_hex, balance_hex, chain_hex = await asyncio.gather(
            self.rpc.call("eth_getTransactionCount", [self.account.address, "pending"]),
            self.rpc.call("eth_gasPrice"),
            self.rpc.call("eth_getBalance", [self.account.address, "pending"]),
            self.rpc.call("eth_chainId"),
        )
        validate_chain_id(int(chain_hex, 16), self.config.chain_id)
        nonce = int(nonce_hex, 16)
        gas_price = int(gas_price_hex, 16)
        balance = int(balance_hex, 16)
        timings["refresh"] = (time.perf_counter_ns() - refresh_ns) / 1_000_000

        transaction: dict[str, Any] = {
            "chainId": self.config.chain_id,
            "to": self.contract,
            "nonce": nonce,
            "data": self.calldata,
            "value": self.value_wei,
            "gasPrice": gas_price,
        }
        simulate_ns = time.perf_counter_ns()
        try:
            await self.rpc.call("eth_call", [self._call_object(), "pending"])
            gas_hex = await self.rpc.call(
                "eth_estimateGas",
                [
                    {
                        **self._call_object(),
                        "nonce": as_hex(nonce),
                        "gasPrice": as_hex(gas_price),
                    }
                ],
            )
        except RPCError as exc:
            self.store.transition(self.run_id, MintState.SKIPPED)
            return ExecutionResult(
                MintState.SKIPPED, message=decode_revert(exc), timings_ms=timings
            )
        gas_limit = max(21_000, int(int(gas_hex, 16) * 1.15))
        transaction["gas"] = gas_limit
        timings["simulation"] = (time.perf_counter_ns() - simulate_ns) / 1_000_000

        limits_ns = time.perf_counter_ns()
        try:
            spend = enforce_limits(
                quantity=self.config.target.quantity,
                mint_wei=self.value_wei,
                gas_limit=gas_limit,
                gas_price_wei=gas_price,
                balance_wei=balance,
                max_price_per_nft_wei=eth_to_wei(self.config.limits.max_price_per_nft_eth),
                max_network_fee_wei=eth_to_wei(self.config.limits.max_network_fee_eth),
                max_total_spend_wei=eth_to_wei(self.config.limits.max_total_spend_eth),
                buffer_wei=eth_to_wei(self.config.limits.balance_buffer_eth),
            )
        except LimitViolation as exc:
            self.store.transition(self.run_id, MintState.SKIPPED, timings=timings)
            return ExecutionResult(MintState.SKIPPED, timings_ms=timings, message=f"Blocked: {exc}")
        timings["limits"] = (time.perf_counter_ns() - limits_ns) / 1_000_000

        if dry_run or self.config.mode == ExecutionMode.WATCH:
            self.store.transition(self.run_id, MintState.SKIPPED, timings=timings)
            return ExecutionResult(
                MintState.SKIPPED,
                spend=spend,
                timings_ms=timings,
                message="Dry run: safe to submit",
            )
        if self.config.mode == ExecutionMode.CONFIRM and not confirmed:
            self.store.transition(self.run_id, MintState.SKIPPED, timings=timings)
            return ExecutionResult(
                MintState.SKIPPED,
                spend=spend,
                timings_ms=timings,
                message="Terminal confirmation required",
            )

        sign_ns = time.perf_counter_ns()
        signed = self.account.sign_transaction(transaction)
        raw_hex = "0x" + signed.raw_transaction.hex()
        timings["signing"] = (time.perf_counter_ns() - sign_ns) / 1_000_000
        self.store.transition(self.run_id, MintState.SIGNED, nonce=nonce)

        broadcast_ns = time.perf_counter_ns()
        tx_hash = await self.rpc.broadcast_same_raw(raw_hex)
        timings["broadcast"] = (time.perf_counter_ns() - broadcast_ns) / 1_000_000
        timings["trigger_to_broadcast"] = (time.perf_counter_ns() - trigger_ns) / 1_000_000
        self.store.transition(
            self.run_id, MintState.BROADCAST, nonce=nonce, tx_hash=tx_hash, timings=timings
        )
        self.store.transition(self.run_id, MintState.PENDING)
        receipt = await self._wait_receipt(tx_hash)
        state = (
            MintState.CONFIRMED if int(receipt.get("status", "0x0"), 16) == 1 else MintState.FAILED
        )
        self.store.transition(self.run_id, state, timings=timings)
        return ExecutionResult(state, tx_hash, receipt, spend, timings)

    async def _wait_receipt(self, tx_hash: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.config.receipt_timeout_seconds
        while time.monotonic() < deadline:
            receipt = await self.rpc.call("eth_getTransactionReceipt", [tx_hash])
            if receipt is not None:
                if not isinstance(receipt, dict):
                    raise RPCError("Malformed transaction receipt")
                return receipt
            await asyncio.sleep(0.5)
        raise TimeoutError("Receipt timeout; transaction may still be pending")
