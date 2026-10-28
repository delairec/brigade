from brigade.tick.heartbeat import Heartbeat


def describe_heartbeat(heartbeat: Heartbeat | None) -> dict | None:
    if heartbeat is None:
        return None
    return {"ts": heartbeat.ts, "duration_ms": heartbeat.duration_ms, "actions_applied": heartbeat.actions_applied}
