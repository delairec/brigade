import json

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.corpus.run_awawa import run_awawa
from brigade.errors import BrigadeError
from brigade.ledger.order_done import OrderDone
from brigade.ledger.read_ledger import read_ledger
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime
from brigade.studies.read_study import read_study
from brigade.studies.render_answer import name_answer
from brigade.studies.study_run_context import ANSWER_FILE, STUDY_KIND

NAME = "study"
STUDY_PARAMETER = "name"
NO_ANSWER = None
FRESH_AT_EACH_CALL = False


def _find_last_answered_run(runtime: Runtime, study: str) -> str | None:
    answered = NO_ANSWER
    for entry in read_ledger(runtime.paths.state_root).entries:
        event = entry.event
        if isinstance(event, OrderDone) and (event.kind, event.order) == (STUDY_KIND, study):
            answered = event.run
    return answered


def _read_answer(runtime: Runtime, study: str, run_id: str) -> dict:
    answered = read_study(runtime, study)
    answer_type = answered.answer_type
    name = name_answer(answered, run_id)
    path = runtime.paths.state_root / RUNS_DIRECTORY / run_id / ANSWER_FILE
    shown = json.loads(
        run_awawa(runtime.run_process, path.parent, ("show", f"@{answer_type}.{name}", "--json", str(path))).stdout
    )
    fields = [
        {"name": field["name"], "value": "".join(json.loads(atom) for atom in field["atoms"])}
        for field in shown["fields"]
    ]
    return {"type": answer_type, "name": name, "fields": fields}


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    if STUDY_PARAMETER not in inputs.parameters:
        raise BrigadeError(f"the study collector takes {STUDY_PARAMETER}=<study>")
    study = inputs.parameters[STUDY_PARAMETER]
    run_id = _find_last_answered_run(runtime, study)
    if run_id is None:
        raise BrigadeError(f"@STUDY.{study} has no answer yet")
    answer = _read_answer(runtime, study, run_id)
    return {**describe_collection(NAME, runtime, {"run": run_id}, [answer]), "cache": FRESH_AT_EACH_CALL}
