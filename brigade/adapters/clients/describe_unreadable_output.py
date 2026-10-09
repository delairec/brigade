UNREADABLE_RESULT = {
    "schema_version": 1,
    "outcome": "failed",
    "steps": None,
    "usage": None,
    "session_id": None,
    "duration_ms": None,
    "cost_usd": None,
    "error_class": "unreadable_output",
    "reset": None,
}


def describe_unreadable_output(stderr: str) -> dict:
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    return {**UNREADABLE_RESULT, "message": lines[-1] if lines else None}
