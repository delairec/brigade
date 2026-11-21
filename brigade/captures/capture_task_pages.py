import re
from dataclasses import dataclass
from pathlib import Path

from brigade.recipes.read_project_commands import read_project_commands
from brigade.recipes.recipe_places import RecipePlaces
from brigade.runtime import Runtime
from brigade.system.create_directory import create_directory
from brigade.system.run_process import ProcessRequest
from brigade.system.write_text_file import write_text_file

DOCUMENT_SCHEMA_VERSION = 1
CAPTURE_RECIPE = "capture"
NO_REFERENCE = "the task carries no REFERENCE: no capture"
NO_RECIPE = "the project declares no recipe capture: no capture"
URL_MARK = "://"
HTML_SUFFIX = ".html"
PAGE_PLACEHOLDER = "{page}"
HOME_SHOWN = "~"
HEAD_CLOSING = "</head>"
HIDDEN_ATTRIBUTE = re.compile(r"\s+hidden(?=[\s>])")
PROFILE_DIRECTORY = "profile"
WINDOW_WIDTH = "1440"
CAPTURE_TIMEOUT_S = 300.0


@dataclass(frozen=True)
class CaptureDemand:
    worktree: Path
    places: RecipePlaces
    references: list[dict]
    directory: Path
    home: str


@dataclass(frozen=True)
class _Rendering:
    demand: CaptureDemand
    commands: tuple[tuple[str, ...], ...]


def _describe_captures(demand: CaptureDemand, pages: list[dict], skipped: list[str]) -> dict:
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "directory": str(demand.directory),
        "pages": pages,
        "skipped": skipped,
    }


def _refuse(reference: str) -> str | None:
    if URL_MARK in reference:
        return f"{reference}: a REFERENCE is a repository path, a URL is not captured"
    if not reference.endswith(HTML_SUFFIX):
        return f"{reference}: brigade renders an HTML reference only"
    return None


def _render_delivered(runtime: Runtime, rendering: _Rendering, page: str) -> str:
    records = [
        runtime.run_process(
            ProcessRequest(
                argv=tuple(argument.replace(PAGE_PLACEHOLDER, page) for argument in argv),
                cwd=str(rendering.demand.worktree),
                timeout_s=CAPTURE_TIMEOUT_S,
            )
        )
        for argv in rendering.commands
    ]
    return records[-1].stdout.replace(rendering.demand.home, HOME_SHOWN)


def _reveal_section(tag: re.Match) -> str:
    return HIDDEN_ATTRIBUTE.sub("", tag.group(0))


def _render_reference(demand: CaptureDemand, reference: str, page: str) -> str:
    shown = (demand.worktree / reference).read_text(encoding="utf-8")
    style = f"<style>section[id]:not(#{page}){{display:none!important}}</style>"
    shown = shown.replace(HEAD_CLOSING, f"{style}{HEAD_CLOSING}", 1)
    shown = re.sub(rf'<section\b[^>]*\bid="{re.escape(page)}"[^>]*>', _reveal_section, shown)
    return shown.replace(demand.home, HOME_SHOWN)


def _screenshot(runtime: Runtime, directory: Path, html: Path) -> Path:
    png = html.with_suffix(".png")
    runtime.run_process(
        ProcessRequest(
            argv=(
                "firefox",
                "--headless",
                "--no-remote",
                "--profile",
                str(directory / PROFILE_DIRECTORY),
                "--window-size",
                WINDOW_WIDTH,
                "--screenshot",
                str(png),
                html.as_uri(),
            ),
            cwd=str(directory),
            timeout_s=CAPTURE_TIMEOUT_S,
        )
    )
    return png


def _capture_page(runtime: Runtime, rendering: _Rendering, reference: dict) -> dict:
    demand = rendering.demand
    page = reference["covers"]
    create_directory(demand.directory / PROFILE_DIRECTORY)
    delivered = demand.directory / f"{page}-delivered.html"
    write_text_file(delivered, _render_delivered(runtime, rendering, page))
    shown = demand.directory / f"{page}-reference.html"
    write_text_file(shown, _render_reference(demand, reference["reference"], page))
    return {
        "page": page,
        "delivered": str(_screenshot(runtime, demand.directory, delivered)),
        "reference": str(_screenshot(runtime, demand.directory, shown)),
    }


def capture_task_pages(runtime: Runtime, demand: CaptureDemand) -> dict:
    if not demand.references:
        return _describe_captures(demand, [], [NO_REFERENCE])
    commands = read_project_commands(demand.places, CAPTURE_RECIPE, runtime.run_process)
    if not commands:
        return _describe_captures(demand, [], [NO_RECIPE])
    rendering = _Rendering(demand=demand, commands=commands)
    refusals = [_refuse(reference["reference"]) for reference in demand.references]
    pages = [
        _capture_page(runtime, rendering, reference)
        for reference, refusal in zip(demand.references, refusals, strict=True)
        if refusal is None
    ]
    return _describe_captures(demand, pages, [refusal for refusal in refusals if refusal is not None])
