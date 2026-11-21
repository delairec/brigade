import re
from dataclasses import dataclass
from pathlib import Path

from brigade.recipes.read_project_commands import read_project_commands
from brigade.recipes.recipe_places import RecipePlaces
from brigade.runtime import Runtime
from brigade.system.create_directory import create_directory
from brigade.system.remove_directory import remove_directory
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRequest
from brigade.system.write_text_file import write_text_file

DOCUMENT_SCHEMA_VERSION = 1
CAPTURE_RECIPE = "capture"
SCREENSHOT_PROGRAM = "firefox"
NO_REFERENCE = "the task carries no REFERENCE: no capture"
NO_RECIPE = "the project declares no recipe capture: no capture"
URL_MARK = "://"
HTML_SUFFIX = ".html"
PAGE_PLACEHOLDER = "{page}"
HOME_SHOWN = "~"
HEAD_CLOSING = "</head>"
HIDDEN_ATTRIBUTE = re.compile(r"\s+hidden(?=[\s>])")
SECTION_ID = re.compile(r"[A-Za-z0-9_-]+")
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


def _find_section(page: str) -> re.Pattern:
    return re.compile(rf'<section\b[^>]*\bid="{re.escape(page)}"[^>]*>')


def _refuse(worktree: Path, reference: str, page: str) -> str | None:
    if URL_MARK in reference:
        return f"{reference}: a REFERENCE is a repository path, a URL is not captured"
    if not reference.endswith(HTML_SUFFIX):
        return f"{reference}: brigade renders an HTML reference only"
    if SECTION_ID.fullmatch(page) is None:
        return f"{reference}: the COVERS {page} is not a section id"
    file = (worktree / reference).resolve()
    if not file.is_relative_to(worktree.resolve()):
        return f"{reference}: a REFERENCE is a path inside the repository"
    if not file.is_file():
        return f"{reference}: no such file in the repository"
    if _find_section(page).search(file.read_text(encoding="utf-8")) is None:
        return f"{reference}: no section of the reference has the id {page}"
    return None


@dataclass(frozen=True)
class _Delivered:
    html: str | None
    failure: str | None


def _render_delivered(runtime: Runtime, rendering: _Rendering, page: str) -> _Delivered:
    for argv in rendering.commands:
        record = runtime.run_process(
            ProcessRequest(
                argv=tuple(argument.replace(PAGE_PLACEHOLDER, page) for argument in argv),
                cwd=str(rendering.demand.worktree),
                timeout_s=CAPTURE_TIMEOUT_S,
                acceptable_exit_codes=EVERY_EXIT_CODE,
            )
        )
        if record.exit_code != 0:
            reason = record.stderr.strip().replace(rendering.demand.home, HOME_SHOWN)
            return _Delivered(
                None, f"{page}: the recipe {CAPTURE_RECIPE} failed with exit {record.exit_code}: {reason}"
            )
    return _Delivered(record.stdout.replace(rendering.demand.home, HOME_SHOWN), None)


def _reveal_section(tag: re.Match) -> str:
    return HIDDEN_ATTRIBUTE.sub("", tag.group(0))


def _render_reference(demand: CaptureDemand, reference: str, page: str) -> str:
    shown = (demand.worktree / reference).read_text(encoding="utf-8")
    style = f"<style>section[id]:not(#{page}){{display:none!important}}</style>"
    shown = shown.replace(HEAD_CLOSING, f"{style}{HEAD_CLOSING}", 1)
    shown = _find_section(page).sub(_reveal_section, shown)
    return shown.replace(demand.home, HOME_SHOWN)


def _screenshot(runtime: Runtime, directory: Path, html: Path, address: str) -> Path:
    png = html.with_suffix(".png")
    runtime.run_process(
        ProcessRequest(
            argv=(
                SCREENSHOT_PROGRAM,
                "--headless",
                "--no-remote",
                "--profile",
                str(directory / PROFILE_DIRECTORY),
                "--window-size",
                WINDOW_WIDTH,
                "--screenshot",
                str(png),
                address,
            ),
            cwd=str(directory),
            timeout_s=CAPTURE_TIMEOUT_S,
        )
    )
    return png


def _capture_page(runtime: Runtime, rendering: _Rendering, reference: dict) -> dict | str:
    demand = rendering.demand
    page = reference["covers"]
    rendered = _render_delivered(runtime, rendering, page)
    if rendered.failure is not None:
        return rendered.failure
    create_directory(demand.directory / PROFILE_DIRECTORY)
    delivered = demand.directory / f"{page}-delivered.html"
    write_text_file(delivered, rendered.html)
    shown = demand.directory / f"{page}-reference.html"
    write_text_file(shown, _render_reference(demand, reference["reference"], page))
    captured = {
        "page": page,
        "delivered": str(_screenshot(runtime, demand.directory, delivered, delivered.as_uri())),
        "reference": str(_screenshot(runtime, demand.directory, shown, f"{shown.as_uri()}#{page}")),
    }
    remove_directory(demand.directory / PROFILE_DIRECTORY)
    return captured


def capture_task_pages(runtime: Runtime, demand: CaptureDemand) -> dict:
    if not demand.references:
        return _describe_captures(demand, [], [NO_REFERENCE])
    commands = read_project_commands(demand.places, CAPTURE_RECIPE, runtime.run_process)
    if not commands:
        return _describe_captures(demand, [], [NO_RECIPE])
    rendering = _Rendering(demand=demand, commands=commands)
    outcomes = [
        _refuse(demand.worktree, reference["reference"], reference["covers"])
        or _capture_page(runtime, rendering, reference)
        for reference in demand.references
    ]
    pages = [outcome for outcome in outcomes if isinstance(outcome, dict)]
    return _describe_captures(demand, pages, [outcome for outcome in outcomes if isinstance(outcome, str)])
