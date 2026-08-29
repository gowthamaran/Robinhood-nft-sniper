#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${project_root}"

green='\033[0;32m'
yellow='\033[1;33m'
red='\033[0;31m'
reset='\033[0m'

say() {
  printf '%b\n' "${green}$*${reset}"
}

warn() {
  printf '%b\n' "${yellow}$*${reset}"
}

fail() {
  printf '%b\n' "${red}$*${reset}" >&2
  exit 1
}

as_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    fail "Administrator access is required once to install Python packages."
  fi
}

if [[ "$(uname -s)" != "Linux" ]]; then
  fail "The one-command launcher currently supports Linux VPS hosts only."
fi

if ! command -v apt-get >/dev/null 2>&1; then
  fail "Automatic dependency installation currently supports Ubuntu/Debian only."
fi

say "Robinhood Chain NFT Sniper - secure automatic setup"
say "Checking the VPS and installing anything missing..."

export DEBIAN_FRONTEND=noninteractive
required_packages=(
  ca-certificates
  build-essential
  git
  python3
  python3-pip
  python3-venv
)

python_version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
if [[ -n "${python_version}" ]]; then
  required_packages+=("python${python_version}-venv")
fi

missing_packages=()
for package in "${required_packages[@]}"; do
  if ! dpkg-query -W -f='${Status}' "${package}" 2>/dev/null | grep -q 'install ok installed'; then
    missing_packages+=("${package}")
  fi
done

if [[ "${#missing_packages[@]}" -gt 0 ]]; then
  warn "Installing: ${missing_packages[*]}"
  as_root apt-get update
  as_root apt-get install -y "${missing_packages[@]}"
fi

python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' || \
  fail "Python 3.12 or newer is required. Ubuntu 24.04 is recommended."

if ! python3 -c 'import ensurepip' >/dev/null 2>&1; then
  as_root apt-get install -y "python${python_version}-venv"
fi

venv_broken=false
if [[ -d .venv ]]; then
  if [[ ! -x .venv/bin/python ]]; then
    venv_broken=true
  elif ! .venv/bin/python -c \
    'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1; then
    venv_broken=true
  elif ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
    venv_broken=true
  fi
fi

if [[ "${venv_broken}" == true ]]; then
  failed_venv=".venv.failed.$(date +%s)"
  warn "The previous virtual environment is incomplete. Moving it to ${failed_venv}."
  mv .venv "${failed_venv}"
fi

if [[ ! -x .venv/bin/python ]] || ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
  python3 -m venv .venv
fi

.venv/bin/python -m ensurepip --upgrade
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install .

config_root="${ROBINHOOD_SNIPER_HOME:-${HOME}/.robinhood-sniper}"
install -d -m 700 \
  "${config_root}" \
  "${config_root}/secrets" \
  "${config_root}/logs" \
  "${config_root}/state" \
  "${config_root}/target"

say "Installation complete. Opening the easy menu..."
exec .venv/bin/robinhood-sniper launch
