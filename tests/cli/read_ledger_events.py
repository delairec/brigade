import json
from pathlib import Path


def read_ledger_events(ledger: Path) -> list[dict]:
    lines = "".join(path.read_text() for path in sorted(ledger.glob("*.jsonl"))).splitlines()
    return list(map(json.loads, lines))
