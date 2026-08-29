// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract MockRobinhoodNFT {
    string public name = "Mock Robinhood NFT";
    string public symbol = "MRNFT";
    bool public saleActive;
    uint256 public mintPrice = 0.001 ether;
    uint256 public maxSupply = 10_000;
    uint256 public walletLimit = 2;
    uint256 public totalSupply;
    mapping(address => uint256) public minted;
    mapping(uint256 => address) public ownerOf;

    event SaleStateChanged(bool active);
    event Minted(address indexed minter, uint256 quantity, uint256 paid);

    error SaleNotActive();
    error SoldOut();
    error WalletLimitExceeded();
    error InsufficientPayment();

    function setSaleActive(bool active) external {
        saleActive = active;
        emit SaleStateChanged(active);
    }

    function setMintPrice(uint256 price) external {
        mintPrice = price;
    }

    function mint(uint256 quantity) external payable {
        if (!saleActive) revert SaleNotActive();
        if (totalSupply + quantity > maxSupply) revert SoldOut();
        if (minted[msg.sender] + quantity > walletLimit) revert WalletLimitExceeded();
        if (msg.value != mintPrice * quantity) revert InsufficientPayment();
        for (uint256 i; i < quantity; ++i) {
            ownerOf[++totalSupply] = msg.sender;
        }
        minted[msg.sender] += quantity;
        emit Minted(msg.sender, quantity, msg.value);
    }
}
