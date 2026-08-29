from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from sniper.models import ExecutionMode
from sniper.network.robinhood import get_network


def app_home() -> Path:
    override = os.getenv("ROBINHOOD_SNIPER_HOME")
    return Path(override).expanduser() if override else Path.home() / ".robinhood-sniper"


def ensure_layout(root: Path | None = None) -> Path:
    root = root or app_home()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    for name in ("secrets", "logs", "state"):
        path = root / name
        path.mkdir(mode=0o700, exist_ok=True)
        os.chmod(path, 0o700)
    return root


class RPCSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: HttpUrl
    backups: list[HttpUrl] = Field(default_factory=list, max_length=5)
    websocket: str | None = None
    timeout_seconds: float = Field(default=4.0, ge=0.5, le=30)

    @field_validator("websocket")
    @classmethod
    def websocket_scheme(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith(("ws://", "wss://")):
            raise ValueError("WebSocket URL must start with ws:// or wss://")
        return value

    def all_http(self) -> list[str]:
        return [str(self.primary)] + [str(item) for item in self.backups]


class WalletSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: str
    keystore_path: str


class TargetSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "NFT mint"
    contract: str
    abi_path: str
    function: str
    arguments: list[Any] = Field(default_factory=list)
    quantity: int = Field(default=1, ge=1, le=100)
    transaction_value_eth: Decimal = Field(default=Decimal("0"), ge=0)
    poll_interval_ms: int = Field(default=175, ge=75, le=10_000)


class LimitSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_price_per_nft_eth: Decimal = Field(gt=0)
    max_network_fee_eth: Decimal = Field(gt=0)
    max_total_spend_eth: Decimal = Field(gt=0)
    balance_buffer_eth: Decimal = Field(default=Decimal("0.002"), ge=0)


class TelegramSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    bot_token: str | None = None
    chat_id: str | None = None


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    network: Literal["testnet", "mainnet"] = "testnet"
    chain_id: int = 46630
    rpc: RPCSettings
    wallet: WalletSettings
    target: TargetSettings
    limits: LimitSettings
    mode: ExecutionMode = ExecutionMode.WATCH
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    sequencer_feed_enabled: bool = True
    receipt_timeout_seconds: int = Field(default=120, ge=15, le=600)

    @model_validator(mode="after")
    def correct_chain(self) -> AppConfig:
        expected = get_network(self.network).chain_id
        if self.chain_id != expected:
            raise ValueError(f"{self.network} requires chain ID {expected}")
        return self


def config_path(root: Path | None = None) -> Path:
    return (root or app_home()) / "config.json"


def load_config(root: Path | None = None) -> AppConfig:
    path = config_path(root)
    if not path.exists():
        raise FileNotFoundError("No configuration found. Run: robinhood-sniper setup")
    return AppConfig.model_validate_json(path.read_text(encoding="utf-8"))


def save_config(config: AppConfig, root: Path | None = None) -> Path:
    root = ensure_layout(root)
    path = config_path(root)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(config.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8"
    )
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.chmod(path, 0o600)
    return path
