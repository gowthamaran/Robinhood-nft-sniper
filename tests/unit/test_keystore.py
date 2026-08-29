import stat

import pytest
from eth_account import Account

from sniper.wallet.keystore import KeystoreError, create_keystore, unlock_keystore


def test_keystore_round_trip_and_permissions(tmp_path) -> None:
    original = Account.create()
    path = tmp_path / "secrets" / "wallet.json"
    address = create_keystore(original.key.hex(), "correct horse battery", path)
    unlocked = unlock_keystore(path, "correct horse battery")
    assert unlocked.address == address == original.address
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert original.key.hex() not in path.read_text(encoding="utf-8")


def test_short_password_rejected(tmp_path) -> None:
    with pytest.raises(KeystoreError, match="12"):
        create_keystore(Account.create().key.hex(), "short", tmp_path / "wallet.json")
