import argparse
import json
from pathlib import Path

from brigade.command import Argument, Command
from brigade.errors import BrigadeError
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_project_forge import NO_FORGE, read_project_forge
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runs.locate_source_worktree import locate_source_worktree
from brigade.runtime import Runtime
from brigade.system.read_configuration import CONFIGURATION_REQUIRED, read_configuration
from brigade.system.read_text_file import read_text_file
from brigade.system.validate_document import DocumentInvalid
from brigade.tasks.locate_task_worktree import locate_task_worktree
from brigade.verify.find_opened_task import find_opened_task
from brigade.verify.record_local_verdict import record_local_verdict
from brigade.verify.record_verdict import VerdictDemand, record_verdict
from brigade.verify.validate_verdict import validate_verdict

DOCUMENT_SCHEMA_VERSION = 1
NAMED_BY_THE_BRANCH = None


def _name_judged(document: dict) -> str:
    if "pr" not in document:
        return f"@TASK.{document['task']}"
    return f"#{document['pr']}, @TASK.{document['task']}"


def _render_text(document: dict) -> str:
    text = f"verdict {document['verdict']} of {_name_judged(document)} at {document['head']}"
    if document["login"] is None:
        return text
    return f"{text}, posted as {document['login']}"


def _read_verdict(path: Path) -> dict:
    text = read_text_file(path)
    try:
        verdict = json.loads(text)
    except ValueError:
        raise BrigadeError(f"the verdict file {path} holds no JSON document") from None
    try:
        validate_verdict(verdict)
    except DocumentInvalid as problem:
        raise BrigadeError(f"the verdict file {path}: {problem}") from None
    return verdict


def verify_verdict(request: argparse.Namespace, runtime: Runtime) -> dict:
    verdict = _read_verdict(Path(request.file))
    run_process = runtime.run_process
    root = locate_worktree_root(run_process, Path.cwd())
    project = require_project_at(read_projects(runtime), locate_main_checkout(run_process, root))
    forge_name = read_project_forge(project)
    if forge_name == NO_FORGE:
        source = locate_source_worktree(runtime.paths, root)
        worktree = locate_task_worktree(runtime, source, NAMED_BY_THE_BRANCH)
        return {"schema_version": DOCUMENT_SCHEMA_VERSION, **record_local_verdict(runtime, worktree, verdict)}
    if request.pr is None:
        raise BrigadeError(
            f"@PROJECT.{project.name} acts through the forge {forge_name}: the verdict names its pull request"
        )
    demand = VerdictDemand(
        project_path=read_project_field(project, "PATH"),
        opened=find_opened_task(runtime, project.name, request.pr).opened,
        verdict=verdict,
        forge=runtime.resolve_plugin("forge", forge_name),
        forge_name=forge_name,
        configuration=read_configuration(runtime, CONFIGURATION_REQUIRED),
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **record_verdict(runtime, demand)}


COMMAND = Command(
    path=("verify", "verdict"),
    help="validate the verdict of the verification of the pull request of a task and record it",
    group_help="check the pull request of a task",
    arguments=(
        Argument(
            ("pr",),
            {"type": int, "nargs": "?", "help": "the number of the pull request, none on a project without a forge"},
        ),
        Argument(("--file",), {"required": True, "help": "the file holding the verdict, a JSON document"}),
    ),
    run=verify_verdict,
    render_text=_render_text,
)
