import re
from dataclasses import dataclass
from pathlib import Path

from brigade.captures.slice_capture import CaptureNotSliced, slice_capture
from brigade.errors import ToolFailure
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
SLICE_HEIGHT = 2000


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


def _skip_read(worktree: Path, reference: dict) -> str | None:
    if reference["reads"] is None:
        return None
    read = (worktree / reference["reads"]).resolve()
    if not (read.is_relative_to(worktree.resolve()) and read.is_file()):
        return f"{reference['reference']}: the READ {reference['reads']} names no file of the repository: no capture"
    return f"{reference['reference']}: the section {reference['covers']} is judged by reading {reference['reads']}: no capture"


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


class _ScreenshotFailed(Exception):
    pass


def _request_screenshot(directory: Path, png: Path, address: str) -> ProcessRequest:
    return ProcessRequest(
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
        acceptable_exit_codes=EVERY_EXIT_CODE,
    )


def _screenshot(runtime: Runtime, demand: CaptureDemand, html: Path, address: str) -> Path:
    png = html.with_suffix(".png")
    try:
        record = runtime.run_process(_request_screenshot(demand.directory, png, address))
    except ToolFailure as failure:
        raise _ScreenshotFailed(str(failure)) from None
    if record.exit_code != 0:
        reason = record.stderr.strip().replace(demand.home, HOME_SHOWN)
        raise _ScreenshotFailed(f"{SCREENSHOT_PROGRAM} failed with exit {record.exit_code} on {html.name}: {reason}")
    if not png.is_file():
        raise _ScreenshotFailed(f"{SCREENSHOT_PROGRAM} wrote no {png.name}")
    return png


@dataclass(frozen=True)
class _PageFiles:
    page: str
    delivered: Path
    shown: Path


def _take_screenshots(runtime: Runtime, demand: CaptureDemand, files: _PageFiles) -> dict:
    create_directory(demand.directory / PROFILE_DIRECTORY)
    try:
        return {
            "delivered": _screenshot(runtime, demand, files.delivered, files.delivered.as_uri()),
            "reference": _screenshot(runtime, demand, files.shown, f"{files.shown.as_uri()}#{files.page}"),
        }
    finally:
        remove_directory(demand.directory / PROFILE_DIRECTORY)


def _capture_page(runtime: Runtime, rendering: _Rendering, reference: dict) -> dict | str:
    demand = rendering.demand
    page = reference["covers"]
    rendered = _render_delivered(runtime, rendering, page)
    if rendered.failure is not None:
        return rendered.failure
    create_directory(demand.directory)
    delivered = demand.directory / f"{page}-delivered.html"
    write_text_file(delivered, rendered.html)
    shown = demand.directory / f"{page}-reference.html"
    write_text_file(shown, _render_reference(demand, reference["reference"], page))
    try:
        pngs = _take_screenshots(runtime, demand, _PageFiles(page, delivered, shown))
        return {
            "page": page,
            "delivered": str(pngs["delivered"]),
            "reference": str(pngs["reference"]),
            "delivered_slices": [str(sliced) for sliced in slice_capture(pngs["delivered"], SLICE_HEIGHT)],
            "reference_slices": [str(sliced) for sliced in slice_capture(pngs["reference"], SLICE_HEIGHT)],
        }
    except (_ScreenshotFailed, CaptureNotSliced) as failure:
        return f"{page}: {failure}"


def capture_task_pages(runtime: Runtime, demand: CaptureDemand) -> dict:
    if not demand.references:
        return _describe_captures(demand, [], [NO_REFERENCE])
    commands = read_project_commands(demand.places, CAPTURE_RECIPE, runtime.run_process)
    if not commands:
        return _describe_captures(demand, [], [NO_RECIPE])
    rendering = _Rendering(demand=demand, commands=commands)
    outcomes = [
        _skip_read(demand.worktree, reference)
        or _refuse(demand.worktree, reference["reference"], reference["covers"])
        or _capture_page(runtime, rendering, reference)
        for reference in demand.references
    ]
    pages = [outcome for outcome in outcomes if isinstance(outcome, dict)]
    return _describe_captures(demand, pages, [outcome for outcome in outcomes if isinstance(outcome, str)])
