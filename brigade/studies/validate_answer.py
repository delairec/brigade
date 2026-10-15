import json
import shutil
from pathlib import Path

from brigade.corpus.run_awawa import run_awawa
from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.studies.read_collected import read_collected
from brigade.studies.read_study import Study
from brigade.studies.render_answer import name_answer, render_answer
from brigade.studies.study_run_context import ANSWER_FILE, FIELDS_THE_CLI_FILLS
from brigade.system.write_text_atomically import write_text_atomically

SCHEMA_FILE = "_schema.awawa"
VALIDATION_DIRECTORY = "validation"
SUBMITTED_DIRECTORY = "submitted"
FILLED_DIRECTORY = "filled"
CONFORMING_EXIT_CODE = 0


def _prepare_corpus(runtime: Runtime, directory: Path, answer: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(runtime.paths.config_root / SCHEMA_FILE, directory / SCHEMA_FILE)
    write_text_atomically(directory / ANSWER_FILE, answer)


def _require_conformity(runtime: Runtime, study: Study, directory: Path) -> None:
    record = run_awawa(runtime.run_process, directory, ("lint", "--strict", str(directory)))
    if record.exit_code != CONFORMING_EXIT_CODE:
        diagnostics = (record.stdout + record.stderr).rstrip()
        raise BrigadeError(f"the schema of {study.answer_type} rejects the answer\n{diagnostics}")


def _read_filled_fields(runtime: Runtime, study: Study, run_id: str, directory: Path) -> list[dict]:
    target = f"@{study.answer_type}.{name_answer(study, run_id)}"
    record = run_awawa(runtime.run_process, directory, ("show", target, "--json", str(directory)))
    if record.exit_code != CONFORMING_EXIT_CODE:
        raise BrigadeError(f"the answer holds no {target}")
    return [field for field in json.loads(record.stdout)["fields"] if field["name"] in FIELDS_THE_CLI_FILLS]


def _find_changed_field(submitted: list[dict], filled: list[dict]) -> str | None:
    for field_name in FIELDS_THE_CLI_FILLS:
        kept = [field for field in submitted if field["name"] == field_name]
        expected = [field for field in filled if field["name"] == field_name]
        if kept != expected:
            return field_name
    return None


def _compare_answer(runtime: Runtime, study: Study, run_directory: Path, answer: str) -> None:
    run_id = run_directory.name
    submitted_directory = run_directory / VALIDATION_DIRECTORY / SUBMITTED_DIRECTORY
    filled_directory = run_directory / VALIDATION_DIRECTORY / FILLED_DIRECTORY
    _prepare_corpus(runtime, submitted_directory, answer)
    _require_conformity(runtime, study, submitted_directory)
    _prepare_corpus(runtime, filled_directory, render_answer(study, run_id, read_collected(run_directory)))
    changed = _find_changed_field(
        _read_filled_fields(runtime, study, run_id, submitted_directory),
        _read_filled_fields(runtime, study, run_id, filled_directory),
    )
    if changed is not None:
        raise BrigadeError(f"the answer changed {changed}, a field brigade filled")


def validate_answer(runtime: Runtime, study: Study, run_directory: Path, answer: str) -> None:
    try:
        _compare_answer(runtime, study, run_directory, answer)
    finally:
        shutil.rmtree(run_directory / VALIDATION_DIRECTORY)
