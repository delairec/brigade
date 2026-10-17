import os

from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.step_done import StepDone
from brigade.ledger.step_failed import StepFailed
from brigade.runs.record_run_pid import record_run_pid
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime
from brigade.studies.collect_evidence import collect_evidence
from brigade.studies.judge_evidence import judge_evidence
from brigade.studies.read_study import Study
from brigade.studies.refuse_inbox_output import refuse_inbox_output
from brigade.studies.start_study_run import start_study_run
from brigade.studies.study_run_context import STEPS_DIRECTORY, STUDY_KIND, StudyEquipment, StudyRunContext
from brigade.studies.write_answer import write_answer
from brigade.system.write_json_atomically import write_json_atomically

STEPS = (("collect", collect_evidence), ("judge", judge_evidence), ("output", write_answer))
DONE = "done"
PARKED = "parked"
NO_PARKED_RUN = None


def _find_parked_run(runtime: Runtime, study: Study) -> str | None:
    last_event = None
    for entry in read_ledger(runtime.paths.state_root).entries:
        event = entry.event
        if isinstance(event, OrderStarted | OrderParked | OrderDone) and (event.kind, event.order) == (
            STUDY_KIND,
            study.name,
        ):
            last_event = event
    if isinstance(last_event, OrderParked):
        return last_event.run
    return NO_PARKED_RUN


def _start_run(runtime: Runtime, study: Study, equipment: StudyEquipment, started_run: str | None) -> StudyRunContext:
    run_id = started_run or _find_parked_run(runtime, study) or start_study_run(runtime, study)
    context = StudyRunContext(
        runtime=runtime,
        study=study,
        run_id=run_id,
        run_directory=runtime.paths.state_root / RUNS_DIRECTORY / run_id,
        equipment=equipment,
    )
    record_run_pid(context.run_directory, os.getpid())
    return context


def run_study(runtime: Runtime, study: Study, equipment: StudyEquipment, started_run: str | None) -> dict:
    refuse_inbox_output(study.output)
    context = _start_run(runtime, study, equipment, started_run)
    for step, perform in STEPS:
        result_path = context.run_directory / STEPS_DIRECTORY / f"{step}.json"
        if result_path.is_file():
            continue
        try:
            result = perform(context)
        except BrigadeError as error:
            reason = str(error)
            append_event(
                runtime.paths, runtime.now, StepFailed(kind=STUDY_KIND, run=context.run_id, step=step, reason=reason)
            )
            append_event(
                runtime.paths,
                runtime.now,
                OrderParked(
                    project=study.project,
                    kind=STUDY_KIND,
                    order=study.name,
                    run=context.run_id,
                    step=step,
                    reason=reason,
                ),
            )
            return {"study": study.name, "run": context.run_id, "state": PARKED, "step": step, "reason": reason}
        write_json_atomically(result_path, result)
        append_event(runtime.paths, runtime.now, StepDone(kind=STUDY_KIND, run=context.run_id, step=step))
    append_event(
        runtime.paths,
        runtime.now,
        OrderDone(project=study.project, kind=STUDY_KIND, order=study.name, run=context.run_id),
    )
    return {"study": study.name, "run": context.run_id, "state": DONE}
