from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import aiohttp
from web3 import Web3


class SetupInputError(ValueError):
    pass


def mint_candidates(abi: list[dict[str, Any]]) -> list[dict[str, Any]]:
    common = ("mint", "claim", "purchase", "buy", "publicmint", "mintpublic")
    transaction_functions = [
        item
        for item in abi
        if item.get("type") == "function"
        and item.get("stateMutability") in {"payable", "nonpayable"}
        and any(word in str(item.get("name", "")).lower() for word in common)
    ]

    def rank(item: dict[str, Any]) -> tuple[int, str]:
        name = str(item.get("name", "")).lower()
        position = next((index for index, word in enumerate(common) if word in name), 999)
        return position, name

    return sorted(transaction_functions, key=rank)


def function_signature(item: dict[str, Any]) -> str:
    inputs = ", ".join(
        f"{value.get('type', '?')} {value.get('name', '')}".strip()
        for value in item.get("inputs", [])
    )
    return f"{item.get('name')}({inputs}) [{item.get('stateMutability')}]"


def parse_abi_input(type_name: str, raw: str) -> Any:
    base_type = type_name.split("[", 1)[0]
    if "[" in type_name or base_type == "tuple":
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SetupInputError("Arrays and tuples must be entered as valid JSON") from exc
    if base_type.startswith(("uint", "int")):
        try:
            return int(raw, 0)
        except ValueError as exc:
            raise SetupInputError("Enter a whole number") from exc
    if base_type == "bool":
        normalized = raw.lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
        if normalized in {"2", "false", "no", "n"}:
            return False
        raise SetupInputError("Enter 1/yes for true or 2/no for false")
    if base_type == "address":
        if not Web3.is_address(raw):
            raise SetupInputError("Enter a valid EVM address")
        return Web3.to_checksum_address(raw)
    if base_type.startswith("bytes"):
        if not raw.startswith("0x"):
            raise SetupInputError("Bytes values must start with 0x")
        try:
            bytes.fromhex(raw[2:])
        except ValueError as exc:
            raise SetupInputError("Bytes value is not valid hexadecimal") from exc
        return raw
    return raw


async def download_abi(url: str, destination: Path) -> Path:
    await _require_public_https(url)
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        current_url = url
        for _ in range(4):
            async with session.get(current_url, allow_redirects=False) as response:
                if response.status in {301, 302, 303, 307, 308}:
                    location = response.headers.get("Location")
                    if not location:
                        raise SetupInputError("ABI link returned an empty redirect")
                    current_url = urljoin(current_url, location)
                    await _require_public_https(current_url)
                    continue
                response.raise_for_status()
                content = await response.content.read(2_000_001)
                break
        else:
            raise SetupInputError("ABI link redirected too many times")
    if len(content) > 2_000_000:
        raise SetupInputError("ABI response is larger than the 2 MB safety limit")
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SetupInputError("The ABI link did not return valid JSON") from exc

    if isinstance(payload, dict) and isinstance(payload.get("result"), str):
        try:
            payload = json.loads(payload["result"])
        except json.JSONDecodeError as exc:
            raise SetupInputError("Explorer response did not contain a valid ABI") from exc
    if isinstance(payload, dict) and "abi" in payload:
        payload = payload["abi"]
    if not isinstance(payload, list):
        raise SetupInputError("ABI response must be a JSON ABI list or contract artifact")

    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(destination.parent, 0o700)
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(destination)
    os.chmod(destination, 0o600)
    return destination


async def _require_public_https(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise SetupInputError("ABI link must be a complete HTTPS URL")
    if parsed.username or parsed.password:
        raise SetupInputError("ABI links must not contain embedded credentials")
    loop = asyncio.get_running_loop()
    try:
        addresses = await loop.getaddrinfo(
            parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise SetupInputError("ABI link hostname could not be resolved") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise SetupInputError("ABI links cannot point to private or local network addresses")
