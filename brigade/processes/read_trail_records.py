import json
from pathlib import Path

from brigade.errors import BrigadeError

LINE_END = b"\n"


def _read_record(trail: Path, number: int, line: str) -> dict:
    try:
        return json.loads(line)
    except ValueError:
        raise BrigadeError(f"line {number} of {trail} is not a process record: not a JSON document") from None


def read_trail_records(trail: Path) -> list[dict]:
    written = trail.read_bytes()
    whole = written[: written.rfind(LINE_END) + 1]
    return [_read_record(trail, number, line) for number, line in enumerate(whole.decode("utf-8").splitlines(), 1)]
