import json
from itertools import zip_longest
from pathlib import Path

from brigade.runs.run_locations import CARRIED_NOTES_FILE, NOTES_FILE, SEGMENTS_DIRECTORY

PENDING = None


def _read_segment_number(segment_directory: Path) -> int:
    return int(segment_directory.name)


def _list_carrying_segments(run_directory: Path) -> list[int]:
    carried_notes = (run_directory / SEGMENTS_DIRECTORY).glob(f"*/{CARRIED_NOTES_FILE}")
    carrying = []
    for carried in sorted(carried_notes, key=lambda path: _read_segment_number(path.parent)):
        count = json.loads(carried.read_text(encoding="utf-8"))["carried"]
        carrying += [_read_segment_number(carried.parent)] * count
    return carrying


def _read_notes(run_directory: Path) -> list[dict]:
    notes_file = run_directory / NOTES_FILE
    if not notes_file.exists():
        return []
    return [json.loads(line) for line in notes_file.read_text(encoding="utf-8").splitlines()]


def list_notes(run_directory: Path) -> list[dict]:
    notes = _read_notes(run_directory)
    segments = _list_carrying_segments(run_directory)
    return [{**note, "segment": segment} for note, segment in zip_longest(notes, segments, fillvalue=PENDING)]
