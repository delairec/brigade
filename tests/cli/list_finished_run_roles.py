def list_finished_run_roles(events: list[dict]) -> list[str]:
    return [event["role"] for event in events if event["event"] == "run.finished"]
