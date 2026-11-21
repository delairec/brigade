from dataclasses import dataclass
from pathlib import Path

from brigade.captures.capture_task_pages import CaptureDemand, capture_task_pages
from brigade.captures.describe_captures_section import describe_captures_section
from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.recipes.recipe_places import RecipePlaces
from brigade.runtime import Runtime
from brigade.verify.list_task_references import list_task_references

NO_SECTION = ""


@dataclass(frozen=True)
class CapturePublication:
    worktree: Path
    places: RecipePlaces
    task: str
    corpus: Path
    directory: Path
    forge: object
    environment: dict
    home: str


def _host_captures(runtime: Runtime, publication: CapturePublication, pages: list[dict]) -> dict[str, str]:
    files = [capture for page in pages for capture in (page["delivered"], page["reference"])]
    hosted = publication.forge.host_images(
        {
            "repository": str(publication.worktree),
            "environment": publication.environment,
            "files": files,
            "description": f"captures of @TASK.{publication.task}",
        },
        runtime,
    )
    return dict(zip(files, hosted["urls"], strict=True))


def publish_task_captures(runtime: Runtime, publication: CapturePublication) -> str:
    shown = read_awawa_document(runtime.run_process, publication.corpus, ("show", f"@TASK.{publication.task}"))
    references = list_task_references(shown)
    if not references:
        return NO_SECTION
    captured = capture_task_pages(
        runtime,
        CaptureDemand(
            worktree=publication.worktree,
            places=publication.places,
            references=references,
            directory=publication.directory,
            home=publication.home,
        ),
    )
    if not captured["pages"]:
        return NO_SECTION
    return describe_captures_section(captured["pages"], _host_captures(runtime, publication, captured["pages"]))
