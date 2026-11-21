from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.captures.locate_task_captures import locate_task_captures
from brigade.captures.publish_task_captures import CapturePublication, publish_task_captures
from brigade.captures.replace_captures_section import replace_captures_section
from brigade.git.resolve_commit import resolve_commit
from brigade.recipes.recipe_places import RecipePlaces
from brigade.runtime import Runtime
from brigade.verify.describe_task_references import describe_task_references

HEAD = "HEAD"


@dataclass(frozen=True)
class ReviewCaptureRefresh:
    project: str
    task: str
    worktree: Path
    places: RecipePlaces
    corpus: Path
    pr: int | None
    forge: object | None
    environment: dict


def _lacks_captures(reference: dict) -> bool:
    return reference["refusal"] is None and reference["captures"] is None


def _rewrite_body(runtime: Runtime, refresh: ReviewCaptureRefresh, section: str) -> None:
    asked = {"repository": str(refresh.worktree), "number": refresh.pr, "environment": refresh.environment}
    body = refresh.forge.read_pull_request(asked, runtime)["pull_request"]["body"]
    refresh.forge.rewrite_pull_request_body({**asked, "body": replace_captures_section(body, section)}, runtime)


def refresh_review_captures(runtime: Runtime, document: dict, equip: Callable[[], ReviewCaptureRefresh]) -> dict:
    if not any(_lacks_captures(reference) for reference in document["references"]):
        return document
    refresh = equip()
    head = document["head"]
    if resolve_commit(runtime.run_process, refresh.worktree, HEAD) != head:
        return document
    directory = locate_task_captures(runtime.paths, refresh.project, refresh.task, head)
    publication = CapturePublication(
        worktree=refresh.worktree,
        places=refresh.places,
        task=refresh.task,
        corpus=refresh.corpus,
        directory=directory,
        forge=refresh.forge,
        environment=refresh.environment,
        home=str(runtime.paths.home),
        head=head,
    )
    section = publish_task_captures(runtime, publication)
    if refresh.pr is not None and section:
        _rewrite_body(runtime, refresh, section)
    cited = [
        {"reference": reference["reference"], "covers": reference["covers"]} for reference in document["references"]
    ]
    return {**document, "references": describe_task_references(cited, directory)}
