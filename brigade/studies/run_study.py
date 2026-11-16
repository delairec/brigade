import dataclasses

from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.read_ledger import read_ledger
from brigade.orders.start_order_run import start_order_run
from brigade.recipes.run_order import FIRST_STEP, OrderRun, StepPerformer, run_order
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime
from brigade.studies.collect_evidence import collect_evidence
from brigade.studies.describe_study_order import describe_study_order
from brigade.studies.judge_evidence import judge_evidence
from brigade.studies.read_live_study_runs import read_live_study_runs
from brigade.studies.read_study import Study
from brigade.studies.read_study_recipe import COLLECT_KIND, read_study_recipe
from brigade.studies.study_run_context import STUDY_KIND, StudyEquipment, StudyRunContext
from brigade.studies.write_answer import write_answer

ORDER_KEY = "order"
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


def _refuse_a_live_run(runtime: Runtime, study: Study, equipment: StudyEquipment) -> None:
    for live in read_live_study_runs(runtime.paths.state_root, equipment.is_run_alive):
        if live.study == study.name:
            raise BrigadeError(f"@STUDY.{study.name} is running in run {live.run}")


def _start_new_run(runtime: Runtime, study: Study, equipment: StudyEquipment) -> str:
    run_id = equipment.name_run(runtime.now)
    start_order_run(runtime, describe_study_order(study), read_study_recipe(study), run_id)
    return run_id


def _start_run(runtime: Runtime, study: Study, equipment: StudyEquipment, started_run: str | None) -> StudyRunContext:
    if started_run is None:
        _refuse_a_live_run(runtime, study, equipment)
    run_id = started_run or _find_parked_run(runtime, study) or _start_new_run(runtime, study, equipment)
    context = StudyRunContext(
        runtime=runtime,
        study=study,
        run_id=run_id,
        run_directory=runtime.paths.state_root / RUNS_DIRECTORY / run_id,
        equipment=equipment,
    )
    equipment.record_own_pid(context.run_directory)
    return context


def _narrow_to_collector(context: StudyRunContext, step: dict, run: OrderRun) -> StudyRunContext:
    return dataclasses.replace(
        context,
        study=dataclasses.replace(context.study, collectors=(step["collector"],)),
        first_collector_rank=run.recipe["steps"].index(step) + FIRST_STEP,
    )


def _create_performers(context: StudyRunContext) -> dict[str, StepPerformer]:
    return {
        COLLECT_KIND: lambda step, run: collect_evidence(_narrow_to_collector(context, step, run)),
        "judge": lambda step, run: judge_evidence(context),
        "output": lambda step, run: write_answer(context),
    }


def _park_study(runtime: Runtime, parked: OrderParked) -> None:
    append_event(runtime.paths, runtime.now, parked)


def run_study(runtime: Runtime, study: Study, equipment: StudyEquipment, started_run: str | None) -> dict:
    context = _start_run(runtime, study, equipment, started_run)
    run = OrderRun(
        order=study.name,
        project=study.project,
        recipe=read_study_recipe(study),
        run_id=context.run_id,
        run_directory=context.run_directory,
    )
    outcome = run_order(runtime, run, _create_performers(context), _park_study)
    return {"study": study.name, **{key: value for key, value in outcome.items() if key != ORDER_KEY}}
