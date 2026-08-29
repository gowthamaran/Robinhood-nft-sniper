#!/usr/bin/env bash
set -euo pipefail

install_root="${ROBINHOOD_SNIPER_INSTALL_ROOT:-$PWD/.venv}"
link_target="${HOME}/.local/bin/robinhood-sniper"

if [[ -L "${link_target}" && "$(readlink "${link_target}")" == "${install_root}/bin/robinhood-sniper" ]]; then
  unlink "${link_target}"
fi

echo "Executable removed."
echo "Encrypted wallet/config/state remain in ${ROBINHOOD_SNIPER_HOME:-${HOME}/.robinhood-sniper}."
echo "Delete that directory manually only after backing up anything you need."
