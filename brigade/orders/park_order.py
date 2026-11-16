from brigade.inbox.record_signal import NewSignal, record_signal
from brigade.ledger.append_event import append_event
from brigade.ledger.order_parked import OrderParked
from brigade.runtime import Runtime

SIGNAL_KIND = "order_parked"


def park_order(runtime: Runtime, parked: OrderParked) -> None:
    append_event(runtime.paths, runtime.now, parked)
    record_signal(
        runtime.paths,
        runtime.now,
        NewSignal(
            kind=SIGNAL_KIND,
            project=parked.project,
            fingerprint=f"{SIGNAL_KIND}:{parked.order}:{parked.run}",
            evidence={
                "order": parked.order,
                "recipe": parked.kind,
                "run": parked.run,
                "step": parked.step,
                "reason": parked.reason,
            },
        ),
    )
