from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.system.resolve_plugin import resolve_plugin
from brigade.system.scheduler_shapes import SCHEDULER_ANSWER_SHAPES
from brigade.system.validate_document import DocumentInvalid, validate_document


@dataclass(frozen=True)
class SchedulerQuestion:
    scheduler_name: str
    operation: str
    request: dict


def ask_scheduler(question: SchedulerQuestion, runtime) -> dict:
    scheduler = resolve_plugin("scheduler", question.scheduler_name, runtime)
    answer = getattr(scheduler, question.operation)(question.request, runtime)
    try:
        validate_document(answer, SCHEDULER_ANSWER_SHAPES[question.operation])
    except DocumentInvalid as problem:
        raise BrigadeError(
            f"scheduler plugin {question.scheduler_name} answered {question.operation}: {problem}"
        ) from None
    return answer
