# Nitro sequencer feed

Robinhood Chain is an Arbitrum L2 and publishes the documented feed endpoints in `sniper/network/robinhood.py`. The Nitro feed is a long-lived WebSocket broadcast envelope, not JSON-RPC `eth_subscribe`. Connections normally drop occasionally, so the listener uses bounded exponential reconnect and exposes health/sequence observations.

The feed is provisional soft-finality data and can use compressed message formats. V0.1.0 does not claim full transaction decoding. It remains an optional monitoring signal; RPC/WebSocket polling and immediate final `eth_call` determine whether execution proceeds.

Robinhood also publishes a sequencer RPC endpoint. Direct submission is disabled by default. It should be introduced only after validating accepted methods, timeouts, duplicate responses, forwarding behavior and fallback with testnet transactions.

Primary references:

- Robinhood Chain documentation: Connecting to Robinhood Chain.
- Arbitrum documentation: How to read the sequencer feed.
- Arbitrum documentation: Sequencer architecture and transaction flow.
