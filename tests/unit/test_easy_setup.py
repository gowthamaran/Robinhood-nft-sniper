import pytest

from sniper.setup.easy import (
    SetupInputError,
    download_abi,
    mint_candidates,
    parse_abi_input,
)


def test_easy_setup_only_lists_mint_like_transaction_functions() -> None:
    abi = [
        {"type": "function", "name": "mint", "stateMutability": "payable", "inputs": []},
        {
            "type": "function",
            "name": "setApprovalForAll",
            "stateMutability": "nonpayable",
            "inputs": [],
        },
        {"type": "function", "name": "claimPublic", "stateMutability": "nonpayable", "inputs": []},
    ]
    assert [item["name"] for item in mint_candidates(abi)] == ["mint", "claimPublic"]


@pytest.mark.parametrize(
    ("type_name", "raw", "expected"),
    [
        ("uint256", "2", 2),
        ("bool", "1", True),
        ("bool", "2", False),
        ("uint256[]", "[1, 2]", [1, 2]),
        ("bytes32", "0x12", "0x12"),
        ("string", "public", "public"),
    ],
)
def test_easy_setup_parses_common_abi_values(type_name, raw, expected) -> None:
    assert parse_abi_input(type_name, raw) == expected


@pytest.mark.asyncio
async def test_abi_download_rejects_non_https_before_network(tmp_path) -> None:
    with pytest.raises(SetupInputError, match="HTTPS"):
        await download_abi("http://example.com/abi.json", tmp_path / "abi.json")


@pytest.mark.asyncio
async def test_abi_download_rejects_local_addresses(tmp_path) -> None:
    with pytest.raises(SetupInputError, match="private or local"):
        await download_abi("https://127.0.0.1/abi.json", tmp_path / "abi.json")
