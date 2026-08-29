# Security policy

## Key boundary

The private key is entered through a hidden terminal prompt and encrypted locally with the Ethereum Web3 keystore format. It is decrypted only in process memory immediately before signing. The application has no custody server, browser extension, analytics collector, or remote key API.

Use a new, dedicated, low-value mint wallet. Do not reuse a savings, exchange, hardware-wallet, or primary DeFi key. A VPS can still be compromised by malware or a hostile administrator; local encryption reduces exposure at rest but cannot protect an unlocked process on a compromised host.

## Reporting

Do not open a public issue for a vulnerability. Send a minimal reproduction privately to the repository owner through GitHub's security advisory flow. Never include a real key, token, authenticated RPC URL, or funded transaction.

## Guarantees and limits

- No private key is transmitted by this code.
- No secrets are intentionally logged or stored in SQLite.
- RPC URLs are stored locally and may contain provider credentials; the config is mode `600`.
- Password strength and VPS security remain the operator's responsibility.
- No software can guarantee a mint, a profit, or protection on a compromised operating system.
