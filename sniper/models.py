from __future__ import annotations

from enum import StrEnum


class ExecutionMode(StrEnum):
    WATCH = "watch"
    CONFIRM = "confirm"
    AUTO = "auto"


class MintState(StrEnum):
    IDLE = "IDLE"
    ARMED = "ARMED"
    TRIGGERED = "TRIGGERED"
    SIMULATING = "SIMULATING"
    SIGNED = "SIGNED"
    BROADCAST = "BROADCAST"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


TERMINAL_STATES = {MintState.CONFIRMED, MintState.FAILED, MintState.SKIPPED}


ALLOWED_TRANSITIONS: dict[MintState, set[MintState]] = {
    MintState.IDLE: {MintState.ARMED},
    MintState.ARMED: {MintState.TRIGGERED, MintState.SKIPPED, MintState.FAILED},
    MintState.TRIGGERED: {MintState.SIMULATING, MintState.SKIPPED, MintState.FAILED},
    MintState.SIMULATING: {MintState.SIGNED, MintState.SKIPPED, MintState.FAILED},
    MintState.SIGNED: {MintState.BROADCAST, MintState.FAILED},
    MintState.BROADCAST: {MintState.PENDING, MintState.CONFIRMED, MintState.FAILED},
    MintState.PENDING: {MintState.CONFIRMED, MintState.FAILED},
    MintState.CONFIRMED: set(),
    MintState.FAILED: {MintState.ARMED},
    MintState.SKIPPED: {MintState.ARMED},
}


def require_transition(current: MintState, new: MintState) -> None:
    if new not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"Invalid mint state transition: {current} -> {new}")
