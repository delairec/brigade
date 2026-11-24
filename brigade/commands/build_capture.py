import argparse
from pathlib import Path

from brigade.captures.capture_task_pages import CaptureDemand, capture_task_pages
from brigade.captures.locate_task_captures import locate_task_captures
from brigade.command import Argument, Command
from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.git.resolve_commit import resolve_commit
from brigade.recipes.locate_recipes import locate_recipes
from brigade.registry.read_corpus_workspace import read_corpus_workspace
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.verify.list_task_references import list_task_references


def _render_text(document: dict) -> str:
    pages = [f"{page['page']}: {page['delivered']} | {page['reference']}" for page in document["pages"]]
    return "\n".join([*pages, *document["skipped"]])


def build_capture(request: argparse.Namespace, runtime: Runtime) -> dict:
    run_process = runtime.run_process
    worktree = locate_worktree_root(run_process, Path.cwd())
    project = require_project_at(read_projects(runtime), locate_main_checkout(run_process, worktree))
    corpus = worktree / read_corpus_workspace(project)
    shown = read_awawa_document(run_process, corpus, ("show", f"@TASK.{request.task}"))
    head = resolve_commit(run_process, worktree, "HEAD")
    default_directory = locate_task_captures(runtime.paths, project.name, request.task, head)
    demand = CaptureDemand(
        worktree=worktree,
        places=locate_recipes(worktree, project, runtime.paths),
        references=list_task_references(shown),
        directory=default_directory if request.directory is None else Path(request.directory),
        home=str(runtime.paths.home),
    )
    return capture_task_pages(runtime, demand)


COMMAND = Command(
    path=("build", "capture"),
    help="capture each page the REFERENCE of a task covers, as delivered and as the reference shows it, in PNG files",
    arguments=(
        Argument(("task",), {"help": "the task whose references are captured"}),
        Argument(("--directory",), {"help": "where the captures are written, the state directory by default"}),
    ),
    run=build_capture,
    render_text=_render_text,
)
