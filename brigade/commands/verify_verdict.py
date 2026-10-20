import json
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import FORGE_NAME
from brigade.errors import BrigadeError
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.system.read_configuration import read_configuration
from brigade.system.validate_document import DocumentInvalid
from brigade.verify.find_opened_task import find_opened_task
from brigade.verify.record_verdict import VerdictDemand, record_verdict
from brigade.verify.validate_verdict import validate_verdict

DOCUMENT_SCHEMA_VERSION = 1


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    text = f"verdict {document['verdict']} of #{document['pr']}, @TASK.{document['task']} at {document['head']}"
    if document["login"] is None:
        return text
    return f"{text}, posted as {document['login']}"


def _decide_exit_code(document: dict) -> int:
    return 0


def _read_verdict(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise BrigadeError(f"cannot read {path}: {error.strerror}") from None
    try:
        verdict = json.loads(text)
    except ValueError:
        raise BrigadeError(f"the verdict file {path} holds no JSON document") from None
    try:
        validate_verdict(verdict)
    except DocumentInvalid as problem:
        raise BrigadeError(f"the verdict file {path}: {problem}") from None
    return verdict


def verify_verdict(request, runtime: Runtime) -> dict:
    verdict = _read_verdict(Path(request.file))
    run_process = runtime.run_process
    project = require_project_at(
        read_projects(runtime), locate_main_checkout(run_process, locate_worktree_root(run_process, Path.cwd()))
    )
    demand = VerdictDemand(
        project_path=read_project_field(project, "PATH"),
        opened=find_opened_task(runtime, project.name, request.pr).opened,
        verdict=verdict,
        forge=runtime.resolve_plugin("forge", FORGE_NAME),
        configuration=read_configuration(runtime.paths.configuration_file),
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **record_verdict(runtime, demand)}


COMMAND = Command(
    path=("verify", "verdict"),
    help="validate the verdict of the verification of the pull request of a task and record it",
    group_help="check the pull request of a task",
    arguments=(
        Argument(("pr",), {"type": int, "help": "the number of the pull request"}),
        Argument(("--file",), {"required": True, "help": "the file holding the verdict, a JSON document"}),
    ),
    run=verify_verdict,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
