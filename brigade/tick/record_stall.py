from brigade.inbox.record_signal import NewSignal, record_signal
from brigade.ledger.format_instant import format_instant
from brigade.runtime import Runtime
from brigade.tick.actions import SignalStall

SIGNAL_KIND = "stall"


def record_stall(runtime: Runtime, action: SignalStall) -> None:
    record_signal(
        runtime.paths,
        runtime.now,
        NewSignal(
            kind=SIGNAL_KIND,
            project=action.project,
            fingerprint=f"{SIGNAL_KIND}:{action.project}:{action.wave}:{action.task}",
            evidence={"wave": action.wave, "task": action.task, "last_action": format_instant(action.last_action)},
        ),
    )
