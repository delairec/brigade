from pathlib import Path
from typing import Optional

from brigade.errors import BrigadeError
from brigade.runs.run_locations import RUN_RECORD_FILE, RUNS_DIRECTORY, SEGMENTS_DIRECTORY, STDERR_FILE, STDOUT_FILE


def _read_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _order_segment(segment_directory: Path) -> int:
    return int(segment_directory.name)


def read_run_logs(state_root: Path, run_id: str, tail: Optional[int]) -> list[str]:
    run_directory = state_root / RUNS_DIRECTORY / run_id
    if Path(run_id).name != run_id or not (run_directory / RUN_RECORD_FILE).is_file():
        raise BrigadeError(f"no run {run_id}")
    segments_directory = run_directory / SEGMENTS_DIRECTORY
    segment_directories = []
    if segments_directory.is_dir():
        segment_directories = sorted(
            (path for path in segments_directory.iterdir() if path.name.isdigit()), key=_order_segment
        )
    lines = [
        line
        for segment_directory in segment_directories
        for log in (STDOUT_FILE, STDERR_FILE)
        for line in _read_lines(segment_directory / log)
    ]
    if tail is None:
        return lines
    return lines[-tail:]
