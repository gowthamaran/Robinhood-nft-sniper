from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import aiohttp
from web3 import Web3

API_ROOT = "https://api.opensea.io/api/v2"
MAX_RESPONSE_BYTES = 1_000_000


class OpenSeaError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True, slots=True)
class OpenSeaDrop:
    slug: str
    chain: str
    contract: str
    active: bool
    next_start: datetime | None


@dataclass(frozen=True, slots=True)
class OpenSeaMintTransaction:
    chain: str
    to: str
    data: str
    value_wei: int


def parse_opensea_mint_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or parsed.hostname not in {"opensea.io", "www.opensea.io"}:
        raise OpenSeaError("Use a complete https://opensea.io mint or collection link")
    if parsed.username or parsed.password:
        raise OpenSeaError("OpenSea links must not contain embedded credentials")
    parts = [unquote(part).strip() for part in parsed.path.split("/") if part.strip()]
    for marker in ("collection", "drops", "drop"):
        if marker in parts:
            index = parts.index(marker)
            if index + 1 < len(parts):
                slug = parts[index + 1]
                if slug.replace("-", "").replace("_", "").isalnum():
                    return slug
    raise OpenSeaError(
        "The link must contain /collection/<slug> or /drops/<slug>; "
        "item/listing links are not mints"
    )


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(UTC)


def parse_drop(payload: dict[str, Any], slug: str) -> OpenSeaDrop:
    chain = str(payload.get("chain", "")).lower()
    contract_raw = payload.get("contract_address")
    if not contract_raw and isinstance(payload.get("contract"), dict):
        contract_raw = payload["contract"].get("address")
    if not isinstance(contract_raw, str) or not Web3.is_address(contract_raw):
        raise OpenSeaError("OpenSea did not return a valid drop contract")
    if int(contract_raw, 16) == 0:
        raise OpenSeaError("OpenSea returned the zero address as the drop contract")
    active_stage = payload.get("active_stage")
    next_stage = payload.get("next_stage")
    next_start = (
        _parse_datetime(next_stage.get("start_time")) if isinstance(next_stage, dict) else None
    )
    return OpenSeaDrop(
        slug=slug,
        chain=chain,
        contract=Web3.to_checksum_address(contract_raw),
        active=isinstance(active_stage, dict),
        next_start=next_start,
    )


def parse_mint_transaction(payload: dict[str, Any]) -> OpenSeaMintTransaction:
    chain = str(payload.get("chain", "")).lower()
    target = payload.get("to")
    data = payload.get("data")
    raw_value = payload.get("value")
    if not isinstance(target, str) or not Web3.is_address(target):
        raise OpenSeaError("OpenSea returned an invalid transaction target")
    if not isinstance(data, str) or not data.startswith("0x") or len(data) <= 2 or len(data) % 2:
        raise OpenSeaError("OpenSea returned invalid mint calldata")
    try:
        bytes.fromhex(data[2:])
    except ValueError as exc:
        raise OpenSeaError("OpenSea returned non-hexadecimal mint calldata") from exc
    if len(data) > 262_146:
        raise OpenSeaError("OpenSea mint calldata is larger than the 128 KB safety limit")
    if int(target, 16) == 0:
        raise OpenSeaError("OpenSea returned the zero address as the transaction target")
    try:
        value_wei = int(str(raw_value), 0)
    except (TypeError, ValueError) as exc:
        raise OpenSeaError("OpenSea returned an invalid transaction value") from exc
    if value_wei < 0:
        raise OpenSeaError("OpenSea returned a negative transaction value")
    return OpenSeaMintTransaction(
        chain=chain,
        to=Web3.to_checksum_address(target),
        data=data,
        value_wei=value_wei,
    )


def save_api_key(path: Path, api_key: str) -> None:
    if not api_key or any(character.isspace() for character in api_key):
        raise OpenSeaError("OpenSea returned an invalid API key")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(api_key, encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.chmod(path, 0o600)


class OpenSeaClient:
    def __init__(self, api_key_path: Path) -> None:
        self.api_key_path = api_key_path
        if api_key_path.exists() and api_key_path.stat().st_mode & 0o077:
            raise OpenSeaError("OpenSea API key permissions are unsafe; run chmod 600 on the file")
        self.api_key = (
            api_key_path.read_text(encoding="utf-8").strip() if api_key_path.exists() else ""
        )
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8))

    async def close(self) -> None:
        await self.session.close()

    async def create_instant_key(self) -> None:
        payload = await self._request("POST", "/auth/keys", authenticated=False)
        api_key = payload.get("api_key")
        if not isinstance(api_key, str):
            raise OpenSeaError("OpenSea did not return an API key")
        save_api_key(self.api_key_path, api_key)
        self.api_key = api_key

    async def get_drop(self, slug: str) -> OpenSeaDrop:
        payload = await self._request("GET", f"/drops/{slug}")
        return parse_drop(payload, slug)

    async def build_mint(self, slug: str, minter: str, quantity: int) -> OpenSeaMintTransaction:
        payload = await self._request(
            "POST", f"/drops/{slug}/mint", json_body={"minter": minter, "quantity": quantity}
        )
        return parse_mint_transaction(payload)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, object] | None = None,
        authenticated: bool = True,
        retry_auth: bool = True,
    ) -> dict[str, Any]:
        if authenticated and not self.api_key:
            await self.create_instant_key()
        headers = {"Accept": "application/json"}
        if authenticated:
            headers["x-api-key"] = self.api_key
        async with self.session.request(
            method,
            f"{API_ROOT}{path}",
            headers=headers,
            json=json_body,
            allow_redirects=False,
        ) as response:
            content = await response.content.read(MAX_RESPONSE_BYTES + 1)
            if len(content) > MAX_RESPONSE_BYTES:
                raise OpenSeaError("OpenSea response exceeded the 1 MB safety limit")
            if response.status == 401 and authenticated and retry_auth:
                await self.create_instant_key()
                return await self._request(
                    method,
                    path,
                    json_body=json_body,
                    authenticated=True,
                    retry_auth=False,
                )
            if response.status not in {200, 201}:
                if response.status == 429:
                    retry_after = response.headers.get("Retry-After", "later")
                    raise OpenSeaError(
                        f"OpenSea rate limit reached; retry after {retry_after} second(s)",
                        status=429,
                    )
                messages = {
                    404: "OpenSea drop not found",
                    409: "OpenSea drop is not active yet",
                    422: "OpenSea says this wallet is not currently eligible to mint",
                }
                raise OpenSeaError(
                    messages.get(
                        response.status, f"OpenSea API request failed ({response.status})"
                    ),
                    status=response.status,
                )
        try:
            payload = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OpenSeaError("OpenSea returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise OpenSeaError("OpenSea returned an unexpected response")
        return payload
