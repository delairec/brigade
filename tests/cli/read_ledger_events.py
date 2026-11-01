import json
from pathlib import Path


def read_ledger_events(state: Path) -> list[dict]:
    lines = "".join(path.read_text() for path in sorted((state / "ledger").glob("*.jsonl"))).splitlines()
    return list(map(json.loads, lines))
