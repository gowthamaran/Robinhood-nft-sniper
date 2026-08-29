# Mint contracts and ABIs

The bot accepts only an explicit local ABI, target address, function name and JSON argument list. Use the ABI published by the verified project/explorer and compare the source contract address across multiple official channels. If the contract is a proxy, verify the implementation and active ABI yourself.

The exact transaction `value` is operator-supplied because mint price discovery is contract-specific. The bot will never infer a proof, signature, voucher, phase ID or token ID. Authorization must be legitimately issued for the configured wallet. A failed simulation is a stop signal, not something to bypass.

Overloaded Solidity functions with the same name and argument count are rejected. Use a wrapper ABI containing only the exact intended overload when necessary.
