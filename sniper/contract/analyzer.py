from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eth_typing import ChecksumAddress
from web3 import Web3

from sniper.rpc.client import RPCPool


class ContractError(RuntimeError):
    pass


def load_abi(path: str) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "abi" in payload:
        payload = payload["abi"]
    if not isinstance(payload, list):
        raise ContractError("ABI file must contain a JSON ABI list or an object with an 'abi' list")
    return payload


def validate_contract_address(address: str) -> ChecksumAddress:
    if not Web3.is_address(address):
        raise ContractError("Invalid target contract address")
    return Web3.to_checksum_address(address)


def resolve_function(
    abi: list[dict[str, Any]], function_name: str, argument_count: int
) -> dict[str, Any]:
    matches = [
        item
        for item in abi
        if item.get("type") == "function"
        and item.get("name") == function_name
        and len(item.get("inputs", [])) == argument_count
    ]
    if len(matches) != 1:
        raise ContractError(
            f"Expected one ABI function named {function_name} with {argument_count} arguments; "
            f"found {len(matches)}"
        )
    mutability = matches[0].get("stateMutability")
    if mutability not in {"payable", "nonpayable"}:
        raise ContractError("Selected mint function is not transaction-capable")
    return matches[0]


def encode_call(
    address: str, abi: list[dict[str, Any]], function_name: str, arguments: list[Any]
) -> str:
    resolve_function(abi, function_name, len(arguments))
    contract = Web3().eth.contract(address=validate_contract_address(address), abi=abi)
    try:
        function = contract.get_function_by_name(function_name)(*arguments)
        return str(function._encode_transaction_data())
    except Exception as exc:
        raise ContractError("Arguments do not match the selected ABI function") from exc


async def analyze_contract(
    rpc: RPCPool, address: str, abi: list[dict[str, Any]], function_name: str, arguments: list[Any]
) -> dict[str, object]:
    checksum = validate_contract_address(address)
    bytecode = await rpc.call("eth_getCode", [checksum, "latest"])
    if bytecode in {"0x", "0x0", None}:
        raise ContractError("Target has no deployed bytecode on the selected network")
    selected = resolve_function(abi, function_name, len(arguments))
    functions = {item.get("name") for item in abi if item.get("type") == "function"}
    standard = "unknown"
    if "ownerOf" in functions:
        standard = "ERC-721-like"
    elif "balanceOfBatch" in functions:
        standard = "ERC-1155-like"
    return {
        "address": checksum,
        "bytecode_bytes": (len(bytecode) - 2) // 2,
        "standard": standard,
        "function_signature": f"{function_name}({','.join(x['type'] for x in selected['inputs'])})",
    }
