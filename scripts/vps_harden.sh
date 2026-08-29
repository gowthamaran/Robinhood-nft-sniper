#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo. Review this script before applying it."
  exit 1
fi

apt-get update
apt-get install -y ufw fail2ban unattended-upgrades chrony
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw --force enable
systemctl enable --now fail2ban chrony

echo "Baseline applied. Also enforce SSH keys, disable root login, and restrict the VPS provider account with MFA."
