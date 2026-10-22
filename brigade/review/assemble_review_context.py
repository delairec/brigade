from dataclasses import dataclass

from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_state import TaskState
from brigade.ledger.task_verdict import TaskVerdict
from brigade.runtime import Runtime
from brigade.system.ask_pull_request_details import PullRequestDetailsQuery, ask_pull_request_details
from brigade.system.ask_review_threads import ReviewThreadsQuery, ask_review_threads
from brigade.verify.read_review_mode import APPROVAL_REVIEW, read_review_mode

FORGE_NAME = "github"
CHANGES_REQUESTED_STATE = "changes_requested"


@dataclass(frozen=True)
class ReviewDemand:
    opened: TaskPrOpened
    project_path: str
    forge: object
    environment: dict


def _is_of_task(event, opened: TaskPrOpened) -> bool:
    return (event.wave, event.task) == (opened.wave, opened.task)


def _read_verdict_findings(events: list, opened: TaskPrOpened) -> list[dict]:
    verdicts = [event for event in events if isinstance(event, TaskVerdict) and _is_of_task(event, opened)]
    if not verdicts:
        return []
    return [{"id": str(rank), **finding} for rank, finding in enumerate(verdicts[-1].findings, start=1)]


def _read_findings(runtime: Runtime, demand: ReviewDemand, review: str, events: list) -> list[dict]:
    if review == APPROVAL_REVIEW:
        return ask_review_threads(
            demand.forge,
            FORGE_NAME,
            ReviewThreadsQuery(repository=demand.project_path, number=demand.opened.pr, environment=demand.environment),
            runtime,
        )
    return _read_verdict_findings(events, demand.opened)


def assemble_review_context(runtime: Runtime, demand: ReviewDemand) -> dict:
    opened = demand.opened
    pull_request = ask_pull_request_details(
        demand.forge,
        FORGE_NAME,
        PullRequestDetailsQuery(repository=demand.project_path, number=opened.pr, environment=demand.environment),
        runtime,
    )
    events = [entry.event for entry in read_ledger(runtime.paths.state_root).entries]
    requests = [
        event.reason
        for event in events
        if isinstance(event, TaskState) and _is_of_task(event, opened) and event.state == CHANGES_REQUESTED_STATE
    ]
    review = read_review_mode(runtime, opened.project)
    return {
        "project": opened.project,
        "pr": opened.pr,
        "task": opened.task,
        "head": pull_request["head_sha"],
        "request": requests[-1] if requests else None,
        "review": review,
        "findings": _read_findings(runtime, demand, review, events),
    }
