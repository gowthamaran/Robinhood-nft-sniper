import pytest

from sniper.network.robinhood import MAINNET, TESTNET, get_network, validate_chain_id


def test_network_constants() -> None:
    assert MAINNET.chain_id == 4663
    assert TESTNET.chain_id == 46630
    assert get_network("TESTNET") is TESTNET


def test_wrong_chain_refuses() -> None:
    with pytest.raises(ValueError, match="Wrong chain"):
        validate_chain_id(1, TESTNET.chain_id)


def test_unsupported_configured_chain_refuses() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        validate_chain_id(1, 1)
