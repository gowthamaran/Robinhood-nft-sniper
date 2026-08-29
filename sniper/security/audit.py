from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from sniper.config import app_home, config_path


@dataclass(frozen=True, slots=True)
class SecurityFinding:
    name: str
    ok: bool
    detail: str


def private_mode(path: Path, expected: int) -> SecurityFinding:
    if not path.exists():
        return SecurityFinding(str(path), False, "missing")
    actual = stat.S_IMODE(path.stat().st_mode)
    return SecurityFinding(str(path), actual == expected, f"mode {actual:o}; expected {expected:o}")


def audit_permissions(root: Path | None = None) -> list[SecurityFinding]:
    root = root or app_home()
    findings = [private_mode(root, 0o700)]
    if config_path(root).exists():
        findings.append(private_mode(config_path(root), 0o600))
    secrets = root / "secrets"
    findings.append(private_mode(secrets, 0o700))
    if secrets.exists():
        findings.extend(private_mode(item, 0o600) for item in secrets.iterdir() if item.is_file())
    env_key = os.getenv("ROBINHOOD_SNIPER_PRIVATE_KEY")
    findings.append(
        SecurityFinding(
            "environment private key",
            env_key is None,
            "not set (recommended)"
            if env_key is None
            else "set; encrypted keystore is safer at rest",
        )
    )
    return findings
