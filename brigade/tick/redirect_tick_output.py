import os
from pathlib import Path

STDOUT = 1
STDERR = 2
APPEND = os.O_WRONLY | os.O_APPEND | os.O_CREAT
LOG_FILE_MODE = 0o644


def redirect_tick_output(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log = os.open(log_file, APPEND, LOG_FILE_MODE)
    discarded = os.open(os.devnull, os.O_WRONLY)
    os.dup2(log, STDERR)
    os.dup2(discarded, STDOUT)
    os.close(log)
    os.close(discarded)
