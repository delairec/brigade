import contextlib
import subprocess
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from brigade.errors import CannotWrite, ToolNotFound
from brigade.system.build_process_environment import build_process_environment


@dataclass(frozen=True)
class SpawnRequest:
    argv: tuple[str, ...]
    cwd: str
    environment: dict
    stdin: str | None
    stdout: Path
    stderr: Path


@contextlib.contextmanager
def _open_input(stdin: str | None) -> Iterator[BinaryIO | int]:
    if stdin is None:
        yield subprocess.DEVNULL
        return
    with tempfile.TemporaryFile() as input_file:
        input_file.write(stdin.encode("utf-8"))
        input_file.seek(0)
        yield input_file


def _open_output(path: Path) -> BinaryIO:
    try:
        return open(path, "ab")
    except OSError as error:
        raise CannotWrite(error.filename or path, error) from error


def spawn_process(request: SpawnRequest) -> subprocess.Popen:
    with (
        _open_output(request.stdout) as stdout_file,
        _open_output(request.stderr) as stderr_file,
        _open_input(request.stdin) as stdin_file,
    ):
        try:
            # S603: argv is a tuple run with no shell, as tests/guards/find_subprocess_uses.py holds
            # subprocess-injection: a Django rule whose taint source is any parameter named request, the S603 case
            # nosemgrep: python.django.security.injection.command.subprocess-injection.subprocess-injection
            process = subprocess.Popen(  # noqa: S603
                list(request.argv),
                cwd=request.cwd,
                env={**build_process_environment(), **request.environment},
                stdin=stdin_file,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=True,
            )
        except FileNotFoundError:
            raise ToolNotFound(f"{request.argv[0]} not on PATH") from None
    return process
