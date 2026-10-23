from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.scheduler_installation import SchedulerInstallation
from brigade.system.scheduler_shapes import SCHEDULER_ANSWER_SHAPES
from brigade.system.scheduler_state import SchedulerState
from brigade.system.validate_document import DocumentInvalid, validate_document

ANSWER_KINDS = {"install": SchedulerInstallation, "read_status": SchedulerState}


@dataclass(frozen=True)
class SchedulerQuestion:
    scheduler_name: str
    operation: str
    request: dict


def ask_scheduler(
    scheduler: object, question: SchedulerQuestion, runtime: Runtime
) -> SchedulerInstallation | SchedulerState:
    answer = getattr(scheduler, question.operation)(question.request, runtime)
    try:
        validate_document(answer, SCHEDULER_ANSWER_SHAPES[question.operation])
    except DocumentInvalid as problem:
        raise BrigadeError(
            f"scheduler plugin {question.scheduler_name} answered {question.operation}: {problem}"
        ) from None
    return ANSWER_KINDS[question.operation].from_document(answer)
