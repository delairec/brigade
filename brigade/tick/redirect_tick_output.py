import os
from pathlib import Path

from brigade.system.create_directory import create_directory

STDOUT = 1
STDERR = 2
APPEND = os.O_WRONLY | os.O_APPEND | os.O_CREAT
LOG_FILE_MODE = 0o644


def redirect_tick_output(log_file: Path) -> None:
    create_directory(log_file.parent)
    log = os.open(log_file, APPEND, LOG_FILE_MODE)
    discarded = os.open(os.devnull, os.O_WRONLY)
    os.dup2(log, STDERR)
    os.dup2(discarded, STDOUT)
    os.close(log)
    os.close(discarded)
