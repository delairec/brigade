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
from brigade.review.record_review_answers import AnswersDemand, record_review_answers
from brigade.runtime import Runtime
from brigade.system.read_configuration import read_configuration
from brigade.verify.find_opened_task import find_opened_task

DOCUMENT_SCHEMA_VERSION = 1
PATH_FIELD = "PATH"


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    findings = ", ".join(answer["finding"] for answer in document["answers"])
    text = f"findings answered on #{document['pr']}, @TASK.{document['task']} at {document['head']}: {findings}"
    if document["login"] is None:
        return text
    return f"{text}, posted as {document['login']}"


def _decide_exit_code(document: dict) -> int:
    return 0


def _read_answers(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise BrigadeError(f"cannot read {path}: {error.strerror}") from None
    try:
        return json.loads(text)
    except ValueError:
        raise BrigadeError(f"the answers file {path} holds no JSON document") from None


def review_reply(request, runtime: Runtime) -> dict:
    answers = _read_answers(Path(request.file))
    run_process = runtime.run_process
    project = require_project_at(
        read_projects(runtime), locate_main_checkout(run_process, locate_worktree_root(run_process, Path.cwd()))
    )
    demand = AnswersDemand(
        opened=find_opened_task(runtime, project.name, request.pr).opened,
        project_path=read_project_field(project, PATH_FIELD),
        answers=answers,
        forge=runtime.resolve_plugin("forge", FORGE_NAME),
        configuration=read_configuration(runtime.paths.configuration_file),
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **record_review_answers(runtime, demand)}


COMMAND = Command(
    path=("review", "reply"),
    help="validate the answers to the findings of the review of the pull request of a task and record them",
    group_help="answer the review of the pull request of a task",
    arguments=(
        Argument(("pr",), {"type": int, "help": "the number of the pull request"}),
        Argument(("--file",), {"required": True, "help": "the file holding the answers, a JSON document"}),
    ),
    run=review_reply,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
