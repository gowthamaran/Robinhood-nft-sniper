from __future__ import annotations

import json
import os
from pathlib import Path
from typing import cast

from eth_account import Account
from eth_account.signers.local import LocalAccount


class KeystoreError(RuntimeError):
    pass


def create_keystore(private_key: str, password: str, path: Path) -> str:
    if len(password) < 12:
        raise KeystoreError("Keystore password must contain at least 12 characters")
    try:
        account = Account.from_key(private_key)
        encrypted = Account.encrypt(account.key, password)
    except Exception as exc:
        raise KeystoreError("Invalid private key") from exc

    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(encrypted), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.chmod(path, 0o600)
    return cast(str, account.address)


def unlock_keystore(path: Path, password: str) -> LocalAccount:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        key = Account.decrypt(payload, password)
        return cast(LocalAccount, Account.from_key(key))
    except (OSError, ValueError, KeyError) as exc:
        raise KeystoreError("Could not unlock keystore; check password and file") from exc


def load_local_account(path: Path, password: str | None = None) -> LocalAccount:
    environment_key = os.getenv("ROBINHOOD_SNIPER_PRIVATE_KEY")
    if environment_key:
        try:
            return cast(LocalAccount, Account.from_key(environment_key))
        except Exception as exc:
            raise KeystoreError("Invalid ROBINHOOD_SNIPER_PRIVATE_KEY") from exc
    if password is None:
        raise KeystoreError("A keystore password is required")
    return unlock_keystore(path, password)
