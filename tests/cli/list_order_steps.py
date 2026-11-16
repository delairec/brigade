def list_order_steps(events: list[dict], kind: str) -> list[tuple[str, str | None]]:
    return [(event["event"], event.get("step")) for event in events if event.get("kind") == kind]
