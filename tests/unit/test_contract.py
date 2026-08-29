import json

import pytest

from sniper.contract.analyzer import ContractError, encode_call, load_abi, resolve_function

ABI = [
    {
        "type": "function",
        "name": "mint",
        "stateMutability": "payable",
        "inputs": [{"name": "quantity", "type": "uint256"}],
        "outputs": [],
    }
]


def test_abi_loading_and_encoding(tmp_path) -> None:
    path = tmp_path / "abi.json"
    path.write_text(json.dumps({"abi": ABI}), encoding="utf-8")
    loaded = load_abi(str(path))
    data = encode_call("0x0000000000000000000000000000000000000001", loaded, "mint", [2])
    assert data.startswith("0x")
    assert len(data) == 2 + 8 + 64


def test_unknown_function_rejected() -> None:
    with pytest.raises(ContractError, match="found 0"):
        resolve_function(ABI, "claim", 1)


def test_view_function_rejected() -> None:
    abi = [{**ABI[0], "stateMutability": "view"}]
    with pytest.raises(ContractError, match="transaction-capable"):
        resolve_function(abi, "mint", 1)
