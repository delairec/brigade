from dataclasses import dataclass

from brigade.system.run_process import ProcessRecord, ProcessRequest


@dataclass(frozen=True)
class ProcessAnswer:
    stdout: str = ""
    exit_code: int = 0
    stderr: str = ""


class ScriptedProcessRunner:
    def __init__(self, answers: dict):
        self.answers = answers
        self.argvs = []

    def _find_answer(self, argv: tuple[str, ...]):
        prefixes = [prefix for prefix in self.answers if argv[: len(prefix)] == prefix]
        if not prefixes:
            raise AssertionError(f"no scripted answer for {argv}")
        return self.answers[max(prefixes, key=len)]

    def run(self, request: ProcessRequest) -> ProcessRecord:
        self.argvs.append(request.argv)
        answer = self._find_answer(request.argv)
        if isinstance(answer, Exception):
            raise answer
        return ProcessRecord(
            argv=request.argv,
            cwd=request.cwd,
            exit_code=answer.exit_code,
            stdout=answer.stdout,
            stderr=answer.stderr,
            duration_ms=0,
        )
