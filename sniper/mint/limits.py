from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

WEI_PER_ETH = 10**18


class LimitViolation(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SpendCheck:
    mint_wei: int
    network_fee_wei: int
    total_wei: int
    balance_wei: int


def eth_to_wei(value: Decimal | str | int) -> int:
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    if decimal_value < 0:
        raise ValueError("ETH amount cannot be negative")
    return int((decimal_value * WEI_PER_ETH).to_integral_value(rounding=ROUND_DOWN))


def enforce_limits(
    *,
    quantity: int,
    mint_wei: int,
    gas_limit: int,
    gas_price_wei: int,
    balance_wei: int,
    max_price_per_nft_wei: int,
    max_network_fee_wei: int,
    max_total_spend_wei: int,
    buffer_wei: int = 0,
) -> SpendCheck:
    if quantity < 1:
        raise LimitViolation("Quantity must be positive")
    if mint_wei > max_price_per_nft_wei * quantity:
        raise LimitViolation("Current mint value exceeds max NFT price")
    network_fee = gas_limit * gas_price_wei
    if network_fee > max_network_fee_wei:
        raise LimitViolation("Worst-case network fee exceeds hard limit")
    total = mint_wei + network_fee
    if total > max_total_spend_wei:
        raise LimitViolation("Worst-case total spend exceeds hard limit")
    if total + buffer_wei > balance_wei:
        raise LimitViolation("Wallet balance is insufficient for cost, fee and buffer")
    return SpendCheck(mint_wei, network_fee, total, balance_wei)
