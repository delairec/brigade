import contextlib
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from brigade.errors import CannotWrite
from brigade.system.build_process_environment import build_process_environment
from brigade.system.explain_launch_failure import explain_launch_failure
from brigade.system.process_trace import ProcessTrace


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
        return path.open("ab")
    except OSError as error:
        raise CannotWrite(error.filename or path, error) from error


def spawn_process(
    request: SpawnRequest, record_trace: Callable[[ProcessTrace], None], environment: Mapping[str, str]
) -> subprocess.Popen:
    started = time.monotonic()
    with (
        _open_output(request.stdout) as stdout_file,
        _open_output(request.stderr) as stderr_file,
        _open_input(request.stdin) as stdin_file,
    ):
        try:
            # S603: argv is a tuple run with no shell, as tests/guards/find_subprocess_uses.py holds
            # subprocess-injection: a Django rule whose taint source is any parameter named request, the S603 case
            # ERA001: the nosemgrep line below is the directive semgrep reads, not commented-out code
            # nosemgrep: python.django.security.injection.command.subprocess-injection.subprocess-injection  # noqa: ERA001
            process = subprocess.Popen(  # noqa: S603
                list(request.argv),
                cwd=request.cwd,
                env={**build_process_environment(environment), **request.environment},
                stdin=stdin_file,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=True,
            )
        except FileNotFoundError as missing:
            duration_ms = round((time.monotonic() - started) * 1000)
            outcome, refusal = explain_launch_failure(request.argv, request.cwd, missing)
            record_trace(ProcessTrace(request.argv, request.cwd, outcome, exit_code=None, duration_ms=duration_ms))
            raise refusal from None
    return process
