import os
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

from brigade.errors import ToolFailure, ToolNotFound

INHERITED_VARIABLES = ("PATH", "HOME", "LANG")
INHERITED_PREFIXES = ("LC_", "XDG_", "BRIGADE_")
EVERY_EXIT_CODE = tuple(range(256))


@dataclass(frozen=True)
class ProcessRequest:
    argv: tuple[str, ...]
    cwd: str
    timeout_s: float
    acceptable_exit_codes: tuple[int, ...] = (0,)
    stdin: Optional[str] = None


@dataclass(frozen=True)
class ProcessRecord:
    argv: tuple[str, ...]
    cwd: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


def _build_environment() -> dict[str, str]:
    return {
        name: value
        for name, value in os.environ.items()
        if name in INHERITED_VARIABLES or name.startswith(INHERITED_PREFIXES)
    }


def _describe_input(stdin: Optional[str]) -> dict:
    if stdin is None:
        return {"stdin": subprocess.DEVNULL}
    return {"input": stdin}


def _describe_command(argv: tuple[str, ...]) -> str:
    return " ".join(argv)


def run_process(request: ProcessRequest) -> ProcessRecord:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(request.argv),
            cwd=request.cwd,
            env=_build_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=request.timeout_s,
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
