import subprocess
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from brigade.errors import CommandFailed, ToolFailure
from brigade.system.build_process_environment import build_process_environment
from brigade.system.explain_launch_failure import explain_launch_failure
from brigade.system.process_trace import EXITED, TIMED_OUT, ProcessTrace

EVERY_EXIT_CODE = tuple(range(256))


@dataclass(frozen=True)
class ProcessRequest:
    argv: tuple[str, ...]
    cwd: str
    timeout_s: float
    acceptable_exit_codes: tuple[int, ...] = (0,)
    stdin: str | None = None
    environment: dict = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class ProcessRecord:
    argv: tuple[str, ...]
    cwd: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


def _describe_input(stdin: str | None) -> dict:
    if stdin is None:
        return {"stdin": subprocess.DEVNULL}
    return {"input": stdin}


def _describe_command(argv: tuple[str, ...]) -> str:
    return " ".join(argv)


def _measure_since(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


def _trace(request: ProcessRequest, outcome: str, exit_code: int | None, duration_ms: int) -> ProcessTrace:
    return ProcessTrace(
        argv=request.argv, cwd=request.cwd, outcome=outcome, exit_code=exit_code, duration_ms=duration_ms
    )


def _launch(request: ProcessRequest, environment: Mapping[str, str]) -> subprocess.CompletedProcess:
    # S603: argv is a tuple run with no shell, as tests/guards/find_subprocess_uses.py holds
    # subprocess-injection: a Django rule whose taint source is any parameter named request, the S603 case
    # ERA001: the nosemgrep line below is the directive semgrep reads, not commented-out code
    # nosemgrep: python.django.security.injection.command.subprocess-injection.subprocess-injection  # noqa: ERA001
    return subprocess.run(  # noqa: S603
        list(request.argv),
        cwd=request.cwd,
        env={**build_process_environment(environment), **request.environment},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=request.timeout_s,
        check=False,
        **_describe_input(request.stdin),
    )


def run_process(
    request: ProcessRequest, record_trace: Callable[[ProcessTrace], None], environment: Mapping[str, str]
) -> ProcessRecord:
    started = time.monotonic()
    try:
        completed = _launch(request, environment)
    except FileNotFoundError as missing:
        outcome, refusal = explain_launch_failure(request.argv, request.cwd, missing)
        record_trace(_trace(request, outcome, None, _measure_since(started)))
        raise refusal from None
    except subprocess.TimeoutExpired:
        record_trace(_trace(request, TIMED_OUT, None, _measure_since(started)))
        raise ToolFailure(f"{_describe_command(request.argv)} timed out after {request.timeout_s:g} s") from None
    record = ProcessRecord(
        argv=request.argv,
        cwd=request.cwd,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_ms=_measure_since(started),
    )
    record_trace(_trace(request, EXITED, record.exit_code, record.duration_ms))
    if record.exit_code not in request.acceptable_exit_codes:
        raise CommandFailed(record.argv, record.exit_code, record.stderr)
    return record
