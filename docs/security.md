# Security operations guide

Use one new wallet for one mint campaign and keep only the maximum affordable ETH on it. Generate/import it on the clean VPS, protect the encrypted keystore with a unique password, and never store that password beside the file. Local encryption does not protect an unlocked process or a VPS root compromise.

Before every event:

1. Patch Ubuntu and reboot if required.
2. Verify the repository commit and review changes.
3. Run `security-check`, `doctor`, `benchmark`, and a dry run.
4. Verify contract, chain, ABI, function, arguments, exact value and all three limits independently.
5. Inspect login history, processes and listening ports.
6. After the event, disarm, transfer excess funds, and archive only sanitized public state.

Never expose SSH password auth, copy keys through chat, run the bot as root, combine it with unknown Telegram software, use a shared VPS, or put secrets in systemd, shell history, screenshots, `.env` committed to Git, CI variables for public forks, or issue reports.
