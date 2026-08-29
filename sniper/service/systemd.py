from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def unit_text(executable: str, user: str, home: str) -> str:
    return f"""[Unit]
Description=Robinhood Chain NFT Sniper
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={user}
Environment=HOME={home}
ExecStart={executable} arm
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths={home}/.robinhood-sniper
UMask=0077

[Install]
WantedBy=multi-user.target
"""


def install_unit(destination: Path = Path("/etc/systemd/system/robinhood-sniper.service")) -> Path:
    executable = shutil.which("robinhood-sniper")
    if executable is None:
        raise RuntimeError("robinhood-sniper executable not found")
    sudo_user = os.getenv("SUDO_USER")
    if not sudo_user or sudo_user == "root":
        raise RuntimeError("Run this command with sudo from the dedicated non-root sniper user")
    home = str(Path("/home") / sudo_user)
    destination.write_text(unit_text(executable, sudo_user, home), encoding="utf-8")
    systemctl_path = shutil.which("systemctl")
    if systemctl_path is None:
        raise RuntimeError("systemctl not found")
    subprocess.run([systemctl_path, "daemon-reload"], check=True)  # noqa: S603
    return destination


def systemctl(action: str) -> None:
    allowed = {"start", "stop", "restart", "status"}
    if action not in allowed:
        raise ValueError(f"Unsupported service action: {action}")
    executable = shutil.which("systemctl")
    if executable is None:
        raise RuntimeError("systemctl not found")
    subprocess.run(  # noqa: S603
        [executable, action, "robinhood-sniper.service"], check=True
    )
