from dataclasses import dataclass
from pathlib import Path

from brigade.recipes.render_result import RESULT_TYPE
from brigade.runtime import Runtime
from brigade.studies.choose_answer_publisher import choose_answer_publisher
from brigade.studies.convert_study import Study
from brigade.studies.present_answer import present_answer
from brigade.studies.study_run_context import StudyEquipment, StudyRunContext
from brigade.studies.write_answer import ENTITY_OUTPUT_PREFIX

NOTHING_HANDED = {}
NO_QUESTION = None
NO_COLLECTORS = ()
JUDGING_SLOT = "judging"
ON_DEMAND = None
ACTIVE = "active"


@dataclass(frozen=True)
class ResultHandoff:
    runtime: Runtime
    order: str
    project: str | None
    output: str
    run_id: str
    run_directory: Path
    equipment: StudyEquipment


def hand_result(handoff: ResultHandoff) -> dict:
    if handoff.output.startswith(ENTITY_OUTPUT_PREFIX):
        return NOTHING_HANDED
    answered = Study(
        name=handoff.order,
        project=handoff.project,
        question=NO_QUESTION,
        collectors=NO_COLLECTORS,
        slot=JUDGING_SLOT,
        every=ON_DEMAND,
        output=handoff.output,
        answer_type=RESULT_TYPE,
        status=ACTIVE,
    )
    context = StudyRunContext(
        runtime=handoff.runtime,
        study=answered,
        run_id=handoff.run_id,
        run_directory=handoff.run_directory,
        equipment=handoff.equipment,
    )
    return choose_answer_publisher(handoff.output)(context, present_answer(context))
