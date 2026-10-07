import dataclasses
import sys
import time

from brigade.command import Argument, Command, ExclusiveArguments
from brigade.errors import StandingDown
from brigade.ledger.format_instant import format_instant
from brigade.runtime import Invocation, build_runtime
from brigade.system.hold_lock_without_waiting import hold_lock_without_waiting
from brigade.system.remove_expired_trails import remove_expired_trails
from brigade.system.repeat_until_signalled import repeat_until_signalled
from brigade.system.run_reporting_failure import run_reporting_failure
from brigade.system.trail_locations import TICKS_DIRECTORY, TRAIL_INSTANT_FORMAT, TRAIL_SUFFIX
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
COMMAND_NAME = "tick"


def _locate_heartbeat(runtime):
    return runtime.paths.state_root / HEARTBEAT_NAME


def _locate_lock(runtime):
    return runtime.paths.state_root / LOCK_DIRECTORY / LOCK_NAME


def _locate_trail(runtime):
    return runtime.paths.state_root / TICKS_DIRECTORY / f"{runtime.now.strftime(TRAIL_INSTANT_FORMAT)}{TRAIL_SUFFIX}"


def _tick(runtime) -> dict | None:
    started = time.monotonic()
    with hold_lock_without_waiting(_locate_lock(runtime)) as acquired:
        if not acquired:
            return None
        runtime.trail.locate(_locate_trail(runtime))
        outcome = run_rounds(
            Rounds(
                build_snapshot=lambda: build_snapshot(runtime.now),
                plan=plan,
                apply=apply_actions,
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


def _tick_and_report(verbose: bool) -> None:
    runtime = build_runtime(Invocation(command=COMMAND_NAME, verbose=verbose))
    remove_expired_trails(runtime.paths, runtime.now)
    heartbeat = _tick(runtime)
    if heartbeat is None:
        sys.stderr.write(f"brigade tick: another tick holds {_locate_lock(runtime)}\n")
        return
    sys.stderr.write(
        f"brigade tick: {heartbeat['ts']}: {heartbeat['actions_applied']} actions applied"
        f" in {heartbeat['duration_ms']} ms\n"
    )
    sys.stderr.flush()


def _tick_in_loop(verbose: bool) -> dict:
    ticks_attempted = repeat_until_signalled(
        lambda: run_reporting_failure(lambda: _tick_and_report(verbose), COMMAND_NAME), TICK_INTERVAL_S
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "mode": "loop", "ticks_attempted": ticks_attempted}


def _render_once(document: dict) -> list[str]:
    return [f"tick {document['ts']}: {document['actions_applied']} actions applied in {document['duration_ms']} ms"]


def _render_dry_run(document: dict) -> list[str]:
    snapshot_lines = [f"  {key}  {value}" for key, value in document["snapshot"].items() if key != "schema_version"]
    plan_lines = [f"  {action}" for action in document["plan"]] or ["  no action"]
    return ["snapshot", *snapshot_lines, "plan", *plan_lines]


def _render_loop(document: dict) -> list[str]:
    return [f"tick --loop: {document['ticks_attempted']} ticks attempted"]


RENDERERS = {"once": _render_once, "dry-run": _render_dry_run, "loop": _render_loop}


def _render_text(document: dict) -> str:
    return "\n".join(RENDERERS[document["mode"]](document))


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def tick(request, runtime) -> dict:
    if request.mode == "once":
        return _tick_once(runtime)
    if request.mode == "dry-run":
        return _plan_dry(runtime)
    return _tick_in_loop(getattr(request, "verbose", False))


COMMAND = Command(
    path=("tick",),
    help="plan and apply what the facts call for, once or in a loop",
    arguments=(
        ExclusiveArguments(
            (
                Argument(
                    ("--once",), {"dest": "mode", "action": "store_const", "const": "once", "help": "run one tick"}
                ),
                Argument(
                    ("--dry-run",),
                    {
                        "dest": "mode",
                        "action": "store_const",
                        "const": "dry-run",
                        "help": "print the snapshot and the plan",
                    },
                ),
                Argument(
                    ("--loop",),
                    {
                        "dest": "mode",
                        "action": "store_const",
                        "const": "loop",
                        "help": "run a tick every five minutes until a signal",
                    },
                ),
            ),
            required=True,
        ),
    ),
    run=tick,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
