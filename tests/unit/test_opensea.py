from datetime import UTC, datetime

import pytest

from sniper.opensea import OpenSeaError, parse_drop, parse_mint_transaction, parse_opensea_mint_url


def test_parse_opensea_collection_and_drop_urls() -> None:
    assert parse_opensea_mint_url("https://opensea.io/collection/robin-drop") == "robin-drop"
    assert parse_opensea_mint_url("https://www.opensea.io/drops/robin_drop") == "robin_drop"


@pytest.mark.parametrize(
    "url",
    [
        "http://opensea.io/collection/drop",
        "https://evil.example/collection/drop",
        "https://opensea.io/assets/robinhood/0x123/1",
    ],
)
def test_parse_opensea_url_rejects_unsafe_or_non_mint_links(url: str) -> None:
    with pytest.raises(OpenSeaError):
        parse_opensea_mint_url(url)


def test_parse_drop_validates_and_normalizes_contract() -> None:
    drop = parse_drop(
        {
            "chain": "robinhood",
            "contract_address": "0x0000000000000000000000000000000000000001",
            "active_stage": None,
            "next_stage": {"start_time": "2026-08-29T22:00:00Z"},
        },
        "robin-drop",
    )
    assert drop.chain == "robinhood"
    assert drop.contract == "0x0000000000000000000000000000000000000001"
    assert drop.next_start == datetime(2026, 8, 29, 22, tzinfo=UTC)
    assert not drop.active


def test_parse_mint_transaction_validates_fields() -> None:
    transaction = parse_mint_transaction(
        {
            "chain": "robinhood",
            "to": "0x0000000000000000000000000000000000000002",
            "data": "0x1234",
            "value": "1000000000000000",
        }
    )
    assert transaction.chain == "robinhood"
    assert transaction.value_wei == 1_000_000_000_000_000


def test_parse_mint_transaction_rejects_bad_calldata() -> None:
    with pytest.raises(OpenSeaError):
        parse_mint_transaction(
            {
                "chain": "robinhood",
                "to": "0x0000000000000000000000000000000000000002",
                "data": "not-hex",
                "value": "0",
            }
        )


def test_parse_mint_transaction_rejects_non_hex_calldata() -> None:
    with pytest.raises(OpenSeaError):
        parse_mint_transaction(
            {
                "chain": "robinhood",
                "to": "0x0000000000000000000000000000000000000002",
                "data": "0xzzzz",
                "value": "0",
            }
        )
