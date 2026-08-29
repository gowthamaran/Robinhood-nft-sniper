# Troubleshooting

## Wrong chain

The RPC URL belongs to another network or provider app. Select a Robinhood Chain endpoint whose `eth_chainId` exactly matches `46630` or `4663`.

## Simulation keeps reverting

The mint may be inactive, sold out, priced differently, restricted, or configured with wrong arguments/value. Verify official ABI and authorization. Do not bypass the failure.

## Network fee or total limit blocked

This is intended. Increase a limit only after independently calculating the maximum affordable loss; the bot never raises it automatically.

## Balance check failed

Fund the dedicated wallet with enough ETH for exact mint value, worst-case configured fee and buffer. Do not keep extra funds on it.

## WebSocket or feed disconnects

Execution can continue via HTTP RPC polling. Check provider WebSocket support and VPS egress. Feed reconnect is bounded and does not disable safety checks.

## Duplicate guard blocked rearm

Inspect `robinhood-sniper stats` and the chain receipt. Use `--rearm` only when you deliberately want another mint.
