# Robinhood Chain NFT Sniper

A fast, self-hosted NFT mint bot built specifically for Robinhood Chain.

It sits ready on your VPS before a mint opens. When the configured mint becomes available, it checks the contract, simulates the transaction, enforces your spending limits, signs locally and submits the transaction.

This is not a Robinhood account bot. It does not ask for your Robinhood login, bypass allowlists or create fake proofs.

## Installation

Use a clean Ubuntu 24.04 VPS. Paste this single command:

```bash
if [ -d Robinhood-nft-sniper/.git ]; then git -C Robinhood-nft-sniper pull --ff-only; else git clone https://github.com/gowthamaran/Robinhood-nft-sniper.git; fi && bash Robinhood-nft-sniper/start.sh
```

That is the only installation command you need.

The launcher checks your VPS, installs missing Python packages, repairs failed installations, creates an isolated environment and opens the setup menu.

## How to use it

The bot guides you using simple numbered choices.

### 1. Choose the network

```text
1) Robinhood Chain Testnet
2) Robinhood Chain Mainnet
```

Use testnet first. Mainnet uses real funds.

### 2. Choose your RPC setup

```text
1) Robinhood public RPC
2) Custom RPC
3) Custom RPC + backup RPCs
```

A good custom RPC is recommended when speed matters. The bot validates the chain ID and checks latency before continuing.

### 3. Add your wallet

Use a new, low-value wallet made only for minting.

The private key is entered through a hidden terminal prompt. It is encrypted locally on your VPS and never sent to us, Telegram or any external server.

### 4. Add the mint

Choose the easy OpenSea option or the manual contract option:

```text
1) Paste an OpenSea NFT mint link
2) Paste the NFT contract and provide its verified ABI
```

With option 1, paste the official `https://opensea.io/collection/...` or `https://opensea.io/drops/...` link. The bot verifies that the drop is on Robinhood Chain, gets the contract and builds the mint transaction through OpenSea's official Drops API. You do not need to find a contract address, ABI or mint function.

The bot automatically creates a free OpenSea API key and keeps it in a local file readable only by your VPS user. This is an OpenSea data key, not your wallet key. Free keys expire after seven days; the bot securely replaces an expired key when needed.

The OpenSea link option is for Robinhood Chain mainnet drops listed on OpenSea. For another mint, choose option 2, enter the contract and provide either a direct HTTPS link to its verified ABI or an ABI JSON file already on the VPS.

For a manual target, the bot shows only mint-like functions such as `mint`, `claim`, `purchase` or `buy`. Choose the correct one and enter any required quantity, proof, signature or voucher.

The bot will never create or fake authorization for you.

### 5. Set your limits

You choose:

- maximum NFT price;
- maximum network fee;
- maximum total spend.

These are hard limits. The bot will block the transaction if any limit is exceeded.

### 6. Choose how it runs

```text
1) WATCH   - check and report only
2) CONFIRM - ask before broadcasting
3) AUTO    - broadcast automatically after all checks pass
```

Review the final summary and press `Y` to start.

The next time you run `bash Robinhood-nft-sniper/start.sh`, you can start the saved configuration, create a new one or run safety checks.

## Why it is better than a normal mint bot

Most mint bots start preparing after they notice a mint is open. This bot prepares before it opens.

- Manual mint calldata is prepared in advance; OpenSea calldata is requested only when the drop is active so it stays current.
- OpenSea links use the official Drops API instead of scraping a web page or guessing a mint function.
- RPC connections stay warm.
- Custom and backup RPCs are ranked using speed, reliability and block freshness.
- Wrong-chain RPCs are rejected.
- Nonce, gas, balance and chain ID are refreshed together.
- Every automatic transaction is simulated immediately before signing.
- The same signed transaction can be sent through two healthy RPCs without creating competing transactions.
- Duplicate protection prevents accidental repeated mints after a restart.
- Real timing measurements are recorded instead of showing fake benchmark numbers.

Robinhood Chain uses first-come-first-served transaction ordering. Reducing avoidable preparation time may help, but no bot can guarantee that your transaction arrives first or that a mint succeeds.

## Safety and security

- Your private key is encrypted and stored only on your VPS.
- Signing happens locally.
- Keys are never stored in logs or SQLite.
- RPC credentials and Telegram tokens are redacted from output.
- Telegram is notification-only and cannot execute transactions.
- The bot supports only Robinhood Chain mainnet and testnet.
- A final simulation is mandatory in AUTO mode.
- Price, fee and total-spend limits cannot be silently increased.
- ABI downloads reject insecure links, private-network addresses and oversized files.
- OpenSea links must use the real `opensea.io` HTTPS domain; item and listing links are rejected.
- OpenSea transaction data must be for Robinhood Chain and pass strict address, calldata and value checks.
- OpenSea API responses still go through the same on-chain simulation and hard spending limits before signing.

No software can protect a private key on an already-compromised VPS. Use SSH keys, enable MFA with your VPS provider, keep Ubuntu updated and never run unrelated software on the same server.

Never use your main wallet. Fund the mint wallet only with what you are prepared to lose, and move unused funds out after the mint.

## DYOR

This project is independent and is not affiliated with or endorsed by Robinhood.

NFT mints, smart contracts and automated transactions can fail or result in financial loss. Verify the official contract, ABI, mint price, wallet limits and project links yourself before starting the bot.

**Always DYOR. Never risk money you cannot afford to lose.**
