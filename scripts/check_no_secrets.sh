#!/usr/bin/env bash
set -euo pipefail

tracked="$(git ls-files)"
if [[ -z "${tracked}" ]]; then
  exit 0
fi

if rg -n --hidden --glob '!scripts/check_no_secrets.sh' \
  '(0x)?[0-9a-fA-F]{64}|[0-9]{6,12}:[A-Za-z0-9_-]{30,}' ${tracked}; then
  echo "Potential secret-shaped value found in tracked files."
  exit 1
fi

echo "No private-key or Telegram-token-shaped tracked values found."
