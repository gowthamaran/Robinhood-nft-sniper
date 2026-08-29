#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This installer supports Linux VPS hosts only."
  exit 1
fi

python_bin="${PYTHON_BIN:-python3}"
"${python_bin}" -c 'import sys; raise SystemExit(sys.version_info < (3, 12))' || {
  echo "Python 3.12+ is required."
  exit 1
}

install_root="${ROBINHOOD_SNIPER_INSTALL_ROOT:-$PWD/.venv}"
"${python_bin}" -m venv "${install_root}"
"${install_root}/bin/python" -m pip install --upgrade pip
"${install_root}/bin/pip" install .

config_root="${ROBINHOOD_SNIPER_HOME:-${HOME}/.robinhood-sniper}"
install -d -m 700 "${config_root}" "${config_root}/secrets" "${config_root}/logs" "${config_root}/state"

link_target="${HOME}/.local/bin/robinhood-sniper"
install -d -m 700 "${HOME}/.local/bin"
ln -sfn "${install_root}/bin/robinhood-sniper" "${link_target}"

echo "Installed: ${link_target}"
echo "Ensure ${HOME}/.local/bin is on PATH, then run: robinhood-sniper setup"
