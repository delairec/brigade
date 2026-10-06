import subprocess
import time
from dataclasses import dataclass

from brigade.errors import ToolFailure, ToolNotFound
from brigade.system.build_process_environment import build_process_environment

EVERY_EXIT_CODE = tuple(range(256))


@dataclass(frozen=True)
class ProcessRequest:
    argv: tuple[str, ...]
    cwd: str
    timeout_s: float
    acceptable_exit_codes: tuple[int, ...] = (0,)
    stdin: str | None = None


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


def run_process(request: ProcessRequest) -> ProcessRecord:
    started = time.monotonic()
    try:
        # S603: argv is a tuple run with no shell, as tests/guards/find_subprocess_uses.py holds
        completed = subprocess.run(  # noqa: S603
            list(request.argv),
            cwd=request.cwd,
            env=build_process_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=request.timeout_s,
            check=False,
            **_describe_input(request.stdin),
        )
    except FileNotFoundError:
        raise ToolNotFound(f"{request.argv[0]} not on PATH") from None
    except subprocess.TimeoutExpired:
        raise ToolFailure(f"{_describe_command(request.argv)} timed out after {request.timeout_s:g} s") from None
    record = ProcessRecord(
        argv=request.argv,
        cwd=request.cwd,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_ms=round((time.monotonic() - started) * 1000),
    )
    if record.exit_code not in request.acceptable_exit_codes:
        raise ToolFailure(f"{_describe_command(request.argv)} exited {record.exit_code}: {record.stderr.strip()}")
    return record
