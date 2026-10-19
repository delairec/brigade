import json
from datetime import UTC, datetime
from pathlib import Path

from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.system.trail_writer import TrailWriter

NOW = datetime(2026, 10, 19, 9, 0, 0, tzinfo=UTC)
NO_PATH_NEEDED = ""
ENTITY_NOT_SHOWN = 1


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
) -> Runtime:
    return Runtime(
        run_process=run_process,
        spawn_process=spawn_process,
        paths=Paths(
            config_root=root / "config",
            state_root=root / "state",
            cache_root=root / "cache",
            home=root / "home",
            executable_search_path=NO_PATH_NEEDED,
            run_directory=run_directory,
        ),
        now=NOW,
        read_clock=lambda: NOW,
        entry_point=root / "bin" / "brigade",
        trail=TrailWriter(_report_nothing),
        resolve_plugin=resolve_plugin,
    )


def answer(request: ProcessRequest, stdout: str, exit_code: int = 0, stderr: str = "") -> ProcessRecord:
    return ProcessRecord(
        argv=request.argv, cwd=request.cwd, exit_code=exit_code, stdout=stdout, stderr=stderr, duration_ms=0
    )


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


def answer_from_machine(entities: dict, outputs: dict, request: ProcessRequest) -> ProcessRecord:
    matching = [prefix for prefix in outputs if request.argv[: len(prefix)] == prefix]
    if not matching:
        return answer_from_corpus(entities, request)
    return answer(request, outputs[max(matching, key=len)])


def create_machine_double(entities: dict, outputs: dict):
    return lambda request: answer_from_machine(entities, outputs, request)


def write_operational_corpus(root: Path) -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config" / "_schema.awawa").write_text("", encoding="utf-8")


def write_ledger(root: Path, lines: list[dict]) -> None:
    (root / "state" / "ledger").mkdir(parents=True)
    (root / "state" / "ledger" / "2026-10.jsonl").write_text(
        "".join(f"{json.dumps(line)}\n" for line in lines), encoding="utf-8"
    )
