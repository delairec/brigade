import contextlib
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from typing import BinaryIO

from brigade.system.build_process_environment import build_process_environment
from brigade.system.explain_launch_failure import explain_launch_failure
from brigade.system.line_receiver import LineReceiver

LINE_BUFFERED = 1


@dataclass(frozen=True)
class PipedProcessRequest:
    argv: tuple[str, ...]
    cwd: str


class PipedProcess:
    def __init__(self, process: subprocess.Popen, errors: BinaryIO):
        self.process = process
        self.errors = errors
        self.receiver = LineReceiver(process.stdout)
        self.written = ""

    def send(self, line: str) -> None:
        try:
            self.process.stdin.write(line)
            self.process.stdin.flush()
        except OSError:
            self.stop()

    def receive(self, timeout_s: float) -> str | None:
        return self.receiver.receive(timeout_s)

    def is_running(self) -> bool:
        return self.process.poll() is None

    def describe_failure(self) -> str:
        exit_code = self.process.wait()
        self.stop()
        return self.written or f"exited with code {exit_code}"

    def stop(self) -> None:
        self.process.kill()
        self.process.wait()
        with contextlib.suppress(OSError):
            self.process.stdin.close()
        if not self.errors.closed:
            self.errors.seek(0)
            self.written = self.errors.read().decode("utf-8", errors="replace").strip()
            self.errors.close()


def start_piped_process(request: PipedProcessRequest, environment: Mapping[str, str]) -> PipedProcess:
    errors = tempfile.TemporaryFile()  # noqa: SIM115
    try:
        # nosemgrep: python.django.security.injection.command.subprocess-injection.subprocess-injection  # noqa: ERA001
        process = subprocess.Popen(  # noqa: S603
            list(request.argv),
            cwd=request.cwd,
            env=build_process_environment(environment),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errors,
            text=True,
            encoding="utf-8",
            bufsize=LINE_BUFFERED,
            start_new_session=True,
        )
    except FileNotFoundError as missing:
        errors.close()
        raise explain_launch_failure(request.argv, request.cwd, missing)[1] from None
    return PipedProcess(process, errors)
