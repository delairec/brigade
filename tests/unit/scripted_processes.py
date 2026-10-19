import json
from collections.abc import Callable
from pathlib import Path

from brigade.errors import CommandFailed
from brigade.system.run_process import ProcessRecord, ProcessRequest

ANSWER_DURATION_MS = 7
LINT_REFUSED = 1
STAGED_CHANGES_FOUND = 1


class ScriptedProcesses:
    def __init__(self):
        self._answers: dict[tuple[str, ...], Callable[[ProcessRequest], tuple[int, str, str]]] = {}
        self.requests: list[ProcessRequest] = []

    def answer(self, argv: tuple[str, ...], stdout: str = "", exit_code: int = 0, stderr: str = "") -> None:
        self._answers[tuple(argv)] = lambda request: (exit_code, stdout, stderr)

    def answer_by(self, argv: tuple[str, ...], respond: Callable[[ProcessRequest], tuple[int, str, str]]) -> None:
        self._answers[tuple(argv)] = respond

    def answer_json(self, argv: tuple[str, ...], document: dict) -> None:
        self.answer(argv, stdout=json.dumps(document))

    def answer_entity(self, root: Path, entity_type: str, name: str, fields: tuple[tuple[str, str], ...]) -> None:
        self.answer_json(
            ("awawa", "show", f"@{entity_type}.{name}", "--json", str(root)),
            {"fields": [{"name": field, "atoms": [json.dumps(value)]} for field, value in fields]},
        )

    def answer_entities(self, root: Path, entity_type: str, entities: dict, conditions: tuple[str, ...] = ()) -> None:
        filters = tuple(argument for condition in conditions for argument in ("--where", condition))
        self.answer_json(
            ("awawa", "status", entity_type, *filters, "--json", str(root)),
            {"entities": [{"type": entity_type, "name": name} for name in entities]},
        )
        for name, fields in entities.items():
            self.answer_entity(root, entity_type, name, fields)

    def answer_corpus_change(
        self, root: Path, file_names: tuple[str, ...], message: str, lint_output: str = ""
    ) -> None:
        self.answer(("awawa", "fmt", *(str(root / file_name) for file_name in file_names)))
        self.answer(
            ("awawa", "lint", "--strict", str(root)), exit_code=LINT_REFUSED if lint_output else 0, stdout=lint_output
        )
        self.answer(("git", "add", "--", *file_names))
        self.answer(("git", "diff", "--cached", "--quiet", "--", *file_names), exit_code=STAGED_CHANGES_FOUND)
        self.answer(("git", "commit", "--quiet", "-m", message))

    def list_argvs(self) -> list[tuple[str, ...]]:
        return [request.argv for request in self.requests]

    def __call__(self, request: ProcessRequest) -> ProcessRecord:
        self.requests.append(request)
        respond = self._answers.get(request.argv)
        if respond is None:
            raise AssertionError(f"no answer is scripted for {request.argv} in {request.cwd}")
        exit_code, stdout, stderr = respond(request)
        if exit_code not in request.acceptable_exit_codes:
            raise CommandFailed(request.argv, exit_code, stderr)
        return ProcessRecord(
            argv=request.argv,
            cwd=request.cwd,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=ANSWER_DURATION_MS,
        )
