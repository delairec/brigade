from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_review_answered import TaskReviewAnswered
from brigade.review.assemble_review_context import ReviewDemand, assemble_review_context
from brigade.review.validate_answers import validate_answers
from brigade.runtime import Runtime
from brigade.system.ask_forge_account import ask_forge_account
from brigade.system.ask_thread_reply import ThreadReply, ask_thread_reply
from brigade.system.parse_configuration import Configuration
from brigade.system.read_account_environment import ForgeAccount, read_account_environment
from brigade.system.validate_document import DocumentInvalid
from brigade.verify.read_review_mode import APPROVAL_REVIEW

FORGE_NAME = "github"
CLI_KEY = "cli"
REMEDIATE_SLOT = "remediate"


@dataclass(frozen=True)
class AnswersDemand:
    opened: TaskPrOpened
    project_path: str
    answers: dict
    forge: object
    configuration: Configuration


def _read_environment(runtime: Runtime, demand: AnswersDemand, key: str) -> dict:
    account = ForgeAccount(forge=demand.forge, forge_name=FORGE_NAME, key=key)
    return read_account_environment(account, demand.configuration, runtime)


def _reply_on_threads(runtime: Runtime, demand: AnswersDemand) -> str | None:
    environment = _read_environment(runtime, demand, REMEDIATE_SLOT)
    for answer in demand.answers["answers"]:
        reply = ThreadReply(
            repository=demand.project_path, thread=answer["finding"], body=answer["answer"], environment=environment
        )
        ask_thread_reply(demand.forge, FORGE_NAME, reply, runtime)
    return ask_forge_account(demand.forge, FORGE_NAME, environment, runtime).login


def record_review_answers(runtime: Runtime, demand: AnswersDemand) -> dict:
    opened = demand.opened
    context = assemble_review_context(
        runtime,
        ReviewDemand(
            opened=opened,
            project_path=demand.project_path,
            forge=demand.forge,
            environment=_read_environment(runtime, demand, CLI_KEY),
        ),
    )
    try:
        validate_answers(demand.answers, context["findings"])
    except DocumentInvalid as problem:
        raise BrigadeError(f"the answers are refused: {problem}") from None
    event = TaskReviewAnswered(
        project=opened.project,
        wave=opened.wave,
        task=opened.task,
        pr=opened.pr,
        head=context["head"],
        answers=tuple(demand.answers["answers"]),
        login=_reply_on_threads(runtime, demand) if context["review"] == APPROVAL_REVIEW else None,
    )
    append_event(runtime.paths, runtime.now, event)
    return event.to_document()
