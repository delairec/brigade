from dataclasses import dataclass
from pathlib import Path

from brigade.captures.capture_task_pages import CaptureDemand, capture_task_pages
from brigade.captures.describe_captures_section import describe_captures_section
from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.recipes.recipe_places import RecipePlaces
from brigade.runtime import Runtime
from brigade.system.write_text_file import write_text_file
from brigade.verify.list_task_references import list_task_references

NO_SECTION = ""
SECTION_FILE = "section.md"
NOT_HOSTED = None


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
    head: str


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


def _host_if_public(runtime: Runtime, publication: CapturePublication, pages: list[dict]) -> dict[str, str] | None:
    if publication.forge is None:
        return NOT_HOSTED
    asked = {"repository": str(publication.worktree), "environment": publication.environment}
    if not publication.forge.read_repository_visibility(asked, runtime)["public"]:
        return NOT_HOSTED
    return _host_captures(runtime, publication, pages)


def publish_task_captures(runtime: Runtime, publication: CapturePublication) -> str:
    published = publication.directory / SECTION_FILE
    if published.is_file():
        return published.read_text(encoding="utf-8")
    shown = read_awawa_document(runtime.run_process, publication.corpus, ("show", f"@TASK.{publication.task}"))
    captured = capture_task_pages(
        runtime,
        CaptureDemand(
            worktree=publication.worktree,
            places=publication.places,
            references=list_task_references(shown),
            directory=publication.directory,
            home=publication.home,
        ),
    )
    if not captured["pages"]:
        return NO_SECTION
    urls = _host_if_public(runtime, publication, captured["pages"])
    section = describe_captures_section(captured["pages"], publication.head, urls)
    write_text_file(published, section)
    return section
