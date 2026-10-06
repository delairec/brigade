import dataclasses
import sys
import time
from typing import Optional

from brigade.errors import StandingDown
from brigade.ledger.format_instant import format_instant
from brigade.runtime import build_runtime
from brigade.system.hold_lock_without_waiting import hold_lock_without_waiting
from brigade.system.repeat_until_signalled import repeat_until_signalled
from brigade.system.write_json_atomically import write_json_atomically
from brigade.tick.apply_actions import apply_actions
from brigade.tick.build_snapshot import build_snapshot
from brigade.tick.plan import plan
from brigade.tick.run_rounds import Rounds, run_rounds

DOCUMENT_SCHEMA_VERSION = 1
TICK_INTERVAL_S = 300
ROUND_CAP = 10
HEARTBEAT_NAME = "tick.json"
LOCK_DIRECTORY = "locks"
LOCK_NAME = "tick.lock"


def _locate_heartbeat(runtime):
    return runtime.paths.state_root / HEARTBEAT_NAME


def _locate_lock(runtime):
    return runtime.paths.state_root / LOCK_DIRECTORY / LOCK_NAME


def _tick(runtime) -> Optional[dict]:
    started = time.monotonic()
    with hold_lock_without_waiting(_locate_lock(runtime)) as acquired:
        if not acquired:
            return None
        outcome = run_rounds(
            Rounds(
                build_snapshot=lambda: build_snapshot(runtime.now),
                plan=plan,
                apply=lambda actions: apply_actions(actions, runtime),
                cap=ROUND_CAP,
            )
        )
        heartbeat = {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "ts": format_instant(runtime.now),
            "duration_ms": int((time.monotonic() - started) * 1000),
            "actions_applied": outcome.actions_applied,
        }
        write_json_atomically(_locate_heartbeat(runtime), heartbeat)
    if outcome.capped:
        sys.stderr.write(f"brigade tick: the plan was not empty after {ROUND_CAP} rounds\n")
    return heartbeat


def _tick_once(runtime) -> dict:
    heartbeat = _tick(runtime)
    if heartbeat is None:
        raise StandingDown(f"another tick holds {_locate_lock(runtime)}")
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "mode": "once",
        "ts": heartbeat["ts"],
        "duration_ms": heartbeat["duration_ms"],
        "actions_applied": heartbeat["actions_applied"],
        "heartbeat": str(_locate_heartbeat(runtime)),
    }


def _plan_dry(runtime) -> dict:
    snapshot = build_snapshot(runtime.now)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "mode": "dry-run",
        "snapshot": snapshot.to_document(),
        "plan": [dataclasses.asdict(action) for action in plan(snapshot)],
    }


def _tick_and_report() -> None:
    runtime = build_runtime()
    heartbeat = _tick(runtime)
    if heartbeat is None:
        sys.stderr.write(f"brigade tick: another tick holds {_locate_lock(runtime)}\n")
        return
    sys.stderr.write(
        f"brigade tick: {heartbeat['ts']}: {heartbeat['actions_applied']} actions applied"
        f" in {heartbeat['duration_ms']} ms\n"
    )
    sys.stderr.flush()


def _tick_in_loop() -> dict:
    ticks = repeat_until_signalled(_tick_and_report, TICK_INTERVAL_S)
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "mode": "loop", "ticks": ticks}


def run(request, runtime) -> dict:
    if request.mode == "once":
        return _tick_once(runtime)
    if request.mode == "dry-run":
        return _plan_dry(runtime)
    return _tick_in_loop()
