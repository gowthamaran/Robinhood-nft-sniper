import sqlite3

import pytest

from sniper.models import MintState
from sniper.storage import StateStore


def test_state_machine_and_duplicate_guard(tmp_path) -> None:
    store = StateStore(tmp_path)
    run = store.create_run("0xwallet", "0xcontract")
    store.transition(run, MintState.ARMED)
    store.transition(run, MintState.TRIGGERED)
    store.transition(run, MintState.SIMULATING)
    store.transition(run, MintState.SIGNED, nonce=1)
    assert store.already_broadcast("0xwallet", "0xcontract")


def test_invalid_transition_rejected(tmp_path) -> None:
    store = StateStore(tmp_path)
    run = store.create_run("wallet", "contract")
    with pytest.raises(ValueError, match="Invalid"):
        store.transition(run, MintState.BROADCAST)


def test_same_nonce_cannot_be_signed_twice(tmp_path) -> None:
    store = StateStore(tmp_path)
    first = store.create_run("wallet", "contract")
    store.transition(first, MintState.ARMED)
    store.transition(first, MintState.TRIGGERED)
    store.transition(first, MintState.SIMULATING)
    store.transition(first, MintState.SIGNED, nonce=7)

    second = store.create_run("wallet", "contract")
    store.transition(second, MintState.ARMED)
    store.transition(second, MintState.TRIGGERED)
    store.transition(second, MintState.SIMULATING)
    with pytest.raises(sqlite3.IntegrityError):
        store.transition(second, MintState.SIGNED, nonce=7)
