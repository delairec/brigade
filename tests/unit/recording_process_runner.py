from dataclasses import dataclass

from brigade.errors import CommandFailed
from brigade.system.run_process import ProcessRecord, ProcessRequest


@dataclass(frozen=True)
class ProcessAnswer:
    stdout: str = ""
    exit_code: int = 0
    stderr: str = ""


SILENT_SUCCESS = ProcessAnswer()


class RecordingProcessRunner:
    def __init__(self, answers: dict[tuple[str, ...], ProcessAnswer] | None = None):
        self._answers = answers or {}
        self.requests: list[ProcessRequest] = []

    def __call__(self, request: ProcessRequest) -> ProcessRecord:
        self.requests.append(request)
        answer = self._answers.get(request.argv, SILENT_SUCCESS)
        if answer.exit_code not in request.acceptable_exit_codes:
            raise CommandFailed(request.argv, answer.exit_code, answer.stderr)
        return ProcessRecord(
            argv=request.argv,
            cwd=request.cwd,
            exit_code=answer.exit_code,
            stdout=answer.stdout,
            stderr=answer.stderr,
            duration_ms=0,
        )

    def list_argvs(self) -> list[tuple[str, ...]]:
        return [request.argv for request in self.requests]

    @property
    def commands(self) -> list[tuple[str, tuple[str, ...]]]:
        return [(request.cwd, request.argv) for request in self.requests]
