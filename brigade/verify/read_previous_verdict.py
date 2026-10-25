from dataclasses import dataclass

from brigade.ledger.task_review_answered import TaskReviewAnswered
from brigade.ledger.task_verdict import TaskVerdict


@dataclass(frozen=True)
class VerifiedPullRequest:
    project: str
    task: str
    pr: int


def _is_of_pull_request(event, verified: VerifiedPullRequest) -> bool:
    return (event.project, event.task, event.pr) == (verified.project, verified.task, verified.pr)


def _read_answers(events: list, verified: VerifiedPullRequest) -> dict[str, str]:
    answers = {}
    for event in events:
        if isinstance(event, TaskReviewAnswered) and _is_of_pull_request(event, verified):
            answers.update((answer["finding"], answer["answer"]) for answer in event.answers)
    return answers


def read_previous_verdict(events: list, verified: VerifiedPullRequest) -> dict | None:
    ranks = [
        rank
        for rank, event in enumerate(events)
        if isinstance(event, TaskVerdict) and _is_of_pull_request(event, verified)
    ]
    if not ranks:
        return None
    verdict = events[ranks[-1]]
    answers = _read_answers(events[ranks[-1] + 1 :], verified)
    findings = [
        {"id": str(rank), **finding, "summary": finding.get("summary"), "answer": answers.get(str(rank))}
        for rank, finding in enumerate(verdict.findings, start=1)
    ]
    return {"head": verdict.head, "verdict": verdict.verdict, "findings": findings}
