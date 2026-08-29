# Changelog

## 0.3.0 - 2026-08-29

- Added an OpenSea mint-link option for Robinhood Chain mainnet drops.
- Builds current mint transactions through OpenSea's official Drops API without requiring an ABI.
- Auto-creates and rotates a restricted local OpenSea API key.
- Applies chain, contract-code, calldata, simulation and spending-limit checks to OpenSea mints.
- Updated the README with the new two-choice target setup.

## 0.2.1 - 2026-08-29

- Detects and rebuilds virtual environments where Python exists but pip is missing.
- Replaced the README with a short human guide focused on installation, usage, advantages and safety.
- Added one installation command that updates an existing checkout or clones a new one.

## 0.2.0 - 2026-08-29

- Added one-line `git clone ... && bash .../start.sh` installation.
- Automatically installs the matching Ubuntu `python3.x-venv` package and repairs failed environments.
- Added numbered network, RPC, WebSocket, ABI, function, mode and Telegram choices.
- Added safe HTTPS ABI downloading with redirect, size and private-network protections.
- Added saved-configuration start/reconfigure/safety menu.
- Allows immediate start after the final `Y` without re-entering the new wallet password.

## 0.1.0 - 2026-08-29

- Initial security-first Robinhood Chain release.
- Encrypted local keystore, strict chain validation, multi-RPC health scoring and failover.
- ABI-driven mint encoding, mandatory simulation, hard limits, local signing and duplicate guard.
- Watch, confirm, auto and dry-run execution modes.
- Doctor, benchmark, security-check, stats, profile and systemd service commands.
