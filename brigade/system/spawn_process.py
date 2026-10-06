import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Optional

from brigade.errors import CannotWrite, ToolNotFound
from brigade.system.build_process_environment import build_process_environment


@dataclass(frozen=True)
class SpawnRequest:
    argv: tuple[str, ...]
    cwd: str
    environment: dict
    stdin: Optional[str]
    stdout: Path
    stderr: Path


def _feed(pipe: BinaryIO, data: bytes) -> None:
    try:
        pipe.write(data)
    except BrokenPipeError:
        pass
    finally:
        try:
            pipe.close()
        except BrokenPipeError:
            pass


def _choose_input(stdin: Optional[str]) -> int:
    if stdin is None:
        return subprocess.DEVNULL
    return subprocess.PIPE


def _open_output(path: Path) -> BinaryIO:
    try:
        return open(path, "ab")
    except OSError as error:
        raise CannotWrite(error.filename or path, error) from error


def spawn_process(request: SpawnRequest) -> subprocess.Popen:
    with _open_output(request.stdout) as stdout_file, _open_output(request.stderr) as stderr_file:
        try:
            process = subprocess.Popen(
                list(request.argv),
                cwd=request.cwd,
                env={**build_process_environment(), **request.environment},
                stdin=_choose_input(request.stdin),
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=True,
            )
        except FileNotFoundError:
            raise ToolNotFound(f"{request.argv[0]} not on PATH") from None
    if request.stdin is not None:
        threading.Thread(target=_feed, args=(process.stdin, request.stdin.encode("utf-8")), daemon=True).start()
    return process
