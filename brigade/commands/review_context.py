import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import FORGE_NAME, read_forge_environment
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.review.assemble_review_context import ReviewDemand, assemble_review_context
from brigade.runtime import Runtime
from brigade.system.read_configuration import CONFIGURATION_REQUIRED, read_configuration
from brigade.verify.find_opened_task import find_opened_task

DOCUMENT_SCHEMA_VERSION = 1
CLI_KEY = "cli"
PATH_FIELD = "PATH"
IDENTIFIER_FIELD = "id"


def _render_finding(finding: dict) -> str:
    fields = "".join(f"{name}: {value}\n" for name, value in finding.items() if name != IDENTIFIER_FIELD)
    return f"## {finding[IDENTIFIER_FIELD]}\n{fields}"


def _render_text(document: dict) -> str:
    sections = [
        f"# head\n{document['head']}\n",
        *([] if document["request"] is None else [f"# request\n{document['request']}\n"]),
        f"# review\n{document['review']}\n",
        "# findings\n" + "".join(_render_finding(finding) for finding in document["findings"]),
    ]
    return "\n".join(sections).removesuffix("\n")


def review_context(request: argparse.Namespace, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime, CONFIGURATION_REQUIRED)
    run_process = runtime.run_process
    project = require_project_at(
        read_projects(runtime), locate_main_checkout(run_process, locate_worktree_root(run_process, Path.cwd()))
    )
    demand = ReviewDemand(
        opened=find_opened_task(runtime, project.name, request.pr).opened,
        project_path=read_project_field(project, PATH_FIELD),
        forge=runtime.resolve_plugin("forge", FORGE_NAME),
        environment=read_forge_environment(configuration, CLI_KEY, runtime),
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **assemble_review_context(runtime, demand)}


COMMAND = Command(
    path=("review", "context"),
    help="print in one read the findings the remediation of the pull request of a task answers",
    group_help="answer the review of the pull request of a task",
    arguments=(Argument(("pr",), {"type": int, "help": "the number of the pull request"}),),
    run=review_context,
    render_text=_render_text,
)
