# VPS checklist

- Ubuntu 24.04 LTS, Python 3.12+, non-root dedicated user.
- SSH keys only, root login disabled after a verified second session.
- VPS provider MFA and recovery codes stored offline.
- Firewall allows SSH only; no public dashboard or database.
- `chrony` or another standard time-sync service enabled.
- Automatic security updates; no unrelated bots or browser software.
- `~/.robinhood-sniper` is mode `700`; config/keystore/database are `600`.
- Testnet setup, doctor, benchmark and dry run all pass.
- Use `tmux` initially; do not put passwords into systemd files.
