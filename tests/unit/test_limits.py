from decimal import Decimal

import pytest

from sniper.mint.limits import LimitViolation, enforce_limits, eth_to_wei


def safe_check() -> dict[str, int]:
    return {
        "quantity": 2,
        "mint_wei": 20,
        "gas_limit": 10,
        "gas_price_wei": 2,
        "balance_wei": 100,
        "max_price_per_nft_wei": 10,
        "max_network_fee_wei": 20,
        "max_total_spend_wei": 40,
    }


def test_limits_accept_exact_boundaries() -> None:
    result = enforce_limits(**safe_check())
    assert result.total_wei == 40


def test_eth_conversion_is_decimal_exact() -> None:
    assert eth_to_wei(Decimal("0.000000000000000001")) == 1
    assert eth_to_wei(Decimal("0.049")) == 49_000_000_000_000_000


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("mint_wei", 21, "price"),
        ("gas_price_wei", 3, "network fee"),
        ("max_total_spend_wei", 39, "total spend"),
        ("balance_wei", 39, "balance"),
    ],
)
def test_each_hard_limit_blocks(field: str, value: int, message: str) -> None:
    values = safe_check()
    values[field] = value
    with pytest.raises(LimitViolation, match=message):
        enforce_limits(**values)
