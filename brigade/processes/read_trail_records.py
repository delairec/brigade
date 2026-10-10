import json
from pathlib import Path


def read_trail_records(trail: Path) -> list[dict]:
    return [json.loads(line) for line in trail.read_text(encoding="utf-8").splitlines()]
