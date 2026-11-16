import json
import shutil
from pathlib import Path

from brigade.corpus.run_awawa import run_awawa
from brigade.errors import BrigadeError
from brigade.recipes.find_answer_type import find_answer_type
from brigade.recipes.name_result import name_result
from brigade.recipes.render_result import render_result
from brigade.recipes.run_order import OrderRun
from brigade.runtime import Runtime
from brigade.studies.study_run_context import ANSWER_FILE
from brigade.system.create_directory import create_directory
from brigade.system.delete_path import delete_path
from brigade.system.write_text_atomically import write_text_atomically

SCHEMA_FILE = "_schema.awawa"
VALIDATION_DIRECTORY = "validation"
SUBMITTED_DIRECTORY = "submitted"
FILLED_DIRECTORY = "filled"
CONFORMING_EXIT_CODE = 0
FIELDS_THE_CLI_FILLS = ("ORDER", "RUN", "COLLECTED")


def _prepare_corpus(runtime: Runtime, directory: Path, answer: str) -> None:
    create_directory(directory)
    shutil.copyfile(runtime.paths.config_root / SCHEMA_FILE, directory / SCHEMA_FILE)
    write_text_atomically(directory / ANSWER_FILE, answer)


def _require_conformity(runtime: Runtime, answer_type: str, directory: Path) -> None:
    record = run_awawa(runtime.run_process, directory, ("lint", "--strict", str(directory)))
    if record.exit_code != CONFORMING_EXIT_CODE:
        diagnostics = (record.stdout + record.stderr).rstrip()
        raise BrigadeError(f"the schema of {answer_type} rejects the answer\n{diagnostics}")


def _read_filled_fields(runtime: Runtime, target: str, directory: Path) -> list[dict]:
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


def _compare_answer(runtime: Runtime, run: OrderRun, answer: str) -> None:
    answer_type = find_answer_type(run)
    target = f"@{answer_type}.{name_result(run)}"
    submitted_directory = run.run_directory / VALIDATION_DIRECTORY / SUBMITTED_DIRECTORY
    filled_directory = run.run_directory / VALIDATION_DIRECTORY / FILLED_DIRECTORY
    _prepare_corpus(runtime, submitted_directory, answer)
    _require_conformity(runtime, answer_type, submitted_directory)
    submitted = _read_filled_fields(runtime, target, submitted_directory)
    _prepare_corpus(runtime, filled_directory, render_result(run))
    changed = _find_changed_field(submitted, _read_filled_fields(runtime, target, filled_directory))
    if changed is not None:
        raise BrigadeError(f"the answer changed {changed}, a field brigade filled")


def validate_result(runtime: Runtime, run: OrderRun, answer: str) -> None:
    try:
        _compare_answer(runtime, run, answer)
    finally:
        delete_path(run.run_directory / VALIDATION_DIRECTORY)
