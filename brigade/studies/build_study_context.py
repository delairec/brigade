import json

from brigade.corpus.run_awawa import run_awawa
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime
from brigade.studies.read_collected import read_collected
from brigade.studies.read_study_of_run import read_study_of_run
from brigade.studies.render_answer import render_answer
from brigade.studies.study_run_context import CONTEXT_FILE, FIELDS_THE_CLI_FILLS
from brigade.system.write_json_atomically import write_json_atomically

FIELD_DECLARATION = "FIELD"
PACKAGE_SCHEMA_VERSION = 1


def _list_prose_fields(runtime: Runtime, answer_type: str) -> list[str]:
    root = runtime.paths.config_root
    shown = json.loads(run_awawa(runtime.run_process, root, ("show", answer_type, "--json", str(root))).stdout)
    return [
        field["atoms"][0]
        for field in shown["fields"]
        if field["name"] == FIELD_DECLARATION and field["atoms"][0] not in FIELDS_THE_CLI_FILLS
    ]


def build_study_context(runtime: Runtime, run_id: str) -> dict:
    run_directory = runtime.paths.state_root / RUNS_DIRECTORY / run_id
    study = read_study_of_run(runtime, run_directory)
    collected = read_collected(run_directory)
    root = runtime.paths.config_root
    package = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "study": study.name,
        "run": run_id,
        "question": study.question,
        "collected": collected,
        "answer": render_answer(study, run_id, collected),
        "prose_fields": _list_prose_fields(runtime, study.answer_type),
        "schema": run_awawa(runtime.run_process, root, ("show", study.answer_type, str(root))).stdout,
    }
    write_json_atomically(run_directory / CONTEXT_FILE, package)
    return package
