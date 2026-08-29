from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RobinhoodNetwork:
    name: str
    chain_id: int
    public_rpc: str
    sequencer_feed: str
    sequencer_rpc: str
    explorer: str


MAINNET = RobinhoodNetwork(
    name="mainnet",
    chain_id=4663,
    public_rpc="https://rpc.mainnet.chain.robinhood.com",
    sequencer_feed="wss://feed.mainnet.chain.robinhood.com",
    sequencer_rpc="https://sequencer.mainnet.chain.robinhood.com",
    explorer="https://robinhoodchain.blockscout.com",
)

TESTNET = RobinhoodNetwork(
    name="testnet",
    chain_id=46630,
    public_rpc="https://rpc.testnet.chain.robinhood.com",
    sequencer_feed="wss://feed.testnet.chain.robinhood.com",
    sequencer_rpc="https://sequencer.testnet.chain.robinhood.com",
    explorer="https://explorer.testnet.chain.robinhood.com",
)

NETWORKS = {"mainnet": MAINNET, "testnet": TESTNET}
ALLOWED_CHAIN_IDS = frozenset(network.chain_id for network in NETWORKS.values())


def get_network(name: str) -> RobinhoodNetwork:
    try:
        return NETWORKS[name.lower()]
    except KeyError as exc:
        raise ValueError("Network must be 'testnet' or 'mainnet'") from exc


def validate_chain_id(actual: int, expected: int) -> None:
    if expected not in ALLOWED_CHAIN_IDS:
        raise ValueError(f"Unsupported configured chain ID: {expected}")
    if actual != expected:
        raise ValueError(
            f"Wrong chain: RPC returned {actual}, expected {expected}. Refusing to arm."
        )
