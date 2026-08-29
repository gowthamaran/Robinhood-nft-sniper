# Architecture

The process has four boundaries: immutable Robinhood network constants, configured external endpoints, local secret material, and public transaction state.

Configuration is validated with Pydantic and written atomically with mode `600`. The wallet key is a Web3 keystore under a `700` secrets directory. The RPC pool owns persistent `aiohttp` sessions, validates chain ID and freshness, and ranks only operator-provided URLs. ABI-driven precomputation resolves exactly one function by name and argument count; it never guesses selectors or authorization.

When armed, a successful `eth_call` is the generic activation signal. The execution coroutine concurrently refreshes pending nonce, gas price, balance and chain ID, repeats simulation, estimates gas, checks worst-case spend, signs locally and propagates the exact same bytes to at most two RPCs. SQLite records the state machine without any secret.

Priority is security, correctness, reliability, then latency. Simulation, chain validation and hard limits remain on the hot path.
