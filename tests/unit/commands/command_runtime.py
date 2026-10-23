import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.system.trail_writer import TrailWriter
from tests.unit.create_test_paths import PACKAGE_FILE

NOW = datetime(2026, 10, 19, 9, 0, 0, tzinfo=UTC)
NO_PATH_NEEDED = ""
ENTITY_NOT_SHOWN = 1


@dataclass(frozen=True)
class ProcessAnswer:
    stdout: str = ""
    exit_code: int = 0
    stderr: str = ""


def _report_nothing(trace) -> None:
    pass


def refuse_process(request):
    raise AssertionError(f"the command ran {request.argv}")


def refuse_resolution(kind: str, name: str, **places):
    raise AssertionError(f"the command resolved the {kind} plugin {name}")


def create_runtime(
    root: Path,
    *,
    run_process=refuse_process,
    spawn_process=refuse_process,
    resolve_plugin=refuse_resolution,
    run_directory: Path | None = None,
    executable_search_path: str = NO_PATH_NEEDED,
) -> Runtime:
    return Runtime(
        run_process=run_process,
        spawn_process=spawn_process,
        paths=Paths(
            config_root=root / "config",
            state_root=root / "state",
            cache_root=root / "cache",
            home=root / "home",
            executable_search_path=executable_search_path,
            package_file=PACKAGE_FILE,
            run_directory=run_directory,
        ),
        now=NOW,
        read_clock=lambda: NOW,
        read_monotonic=lambda: 0.0,
        entry_point=root / "bin" / "brigade",
        trail=TrailWriter(_report_nothing),
        resolve_plugin=resolve_plugin,
    )


def answer(request: ProcessRequest, stdout: str, exit_code: int = 0, stderr: str = "") -> ProcessRecord:
    return ProcessRecord(
        argv=request.argv, cwd=request.cwd, exit_code=exit_code, stdout=stdout, stderr=stderr, duration_ms=0
    )


class ScriptedProcessRunner:
    def __init__(self, answers: dict, fallback=refuse_process):
        self.answers = answers
        self.fallback = fallback
        self.argvs = []

    def run(self, request: ProcessRequest) -> ProcessRecord:
        self.argvs.append(request.argv)
        prefixes = [prefix for prefix in self.answers if request.argv[: len(prefix)] == prefix]
        if not prefixes:
            return self.fallback(request)
        scripted = self.answers[max(prefixes, key=len)]
        if isinstance(scripted, Exception):
            raise scripted
        return answer(request, scripted.stdout, scripted.exit_code, scripted.stderr)


def answer_from_corpus(entities: dict, request: ProcessRequest) -> ProcessRecord:
    if request.argv[:2] == ("awawa", "status"):
        listed = [{"type": request.argv[2], "name": name} for name in entities.get(request.argv[2], {})]
        return answer(request, json.dumps({"entities": listed}))
    if request.argv[:2] == ("awawa", "show"):
        entity_type, _, name = request.argv[2].removeprefix("@").partition(".")
        fields = entities.get(entity_type, {}).get(name)
        if fields is None:
            return answer(request, "", ENTITY_NOT_SHOWN, f"{request.argv[2]} is not defined in the workspace")
        shown = [{"name": field, "atoms": [json.dumps(value)]} for field, value in fields]
        return answer(request, json.dumps({"fields": shown}))
    raise AssertionError(f"the command ran {request.argv}")


def create_corpus_double(entities: dict):
    return lambda request: answer_from_corpus(entities, request)


def create_machine_double(entities: dict, outputs: dict):
    answers = {prefix: ProcessAnswer(stdout=stdout) for prefix, stdout in outputs.items()}
    return ScriptedProcessRunner(answers, fallback=create_corpus_double(entities)).run


def write_operational_corpus(root: Path) -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config" / "_schema.awawa").write_text("", encoding="utf-8")


def write_ledger(root: Path, lines: list[dict]) -> None:
    (root / "state" / "ledger").mkdir(parents=True, exist_ok=True)
    (root / "state" / "ledger" / "2026-10.jsonl").write_text(
        "".join(f"{json.dumps(line)}\n" for line in lines), encoding="utf-8"
    )
