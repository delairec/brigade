from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import FORGE_NAME, read_forge_environment
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.system.read_configuration import read_configuration
from brigade.verify.assemble_verify_context import assemble_verify_context
from brigade.verify.find_opened_task import find_opened_task
from brigade.verify.preflight_pull_request import PreflightDemand

DOCUMENT_SCHEMA_VERSION = 1
CLI_KEY = "cli"


def _read_request(options):
    return options


def _render_commands(entries: list[dict]) -> str:
    return "".join(
        f"$ {entry['command']}\nexit {entry['exit_code']}\n{entry['stderr']}{entry['output']}" for entry in entries
    )


def _render_preflight(checks: list[dict]) -> str:
    return "".join(
        f"{check['verdict']}  {check['name']}\n" + "".join(f"  {finding}\n" for finding in check["findings"])
        for check in checks
    )


def _render_text(document: dict) -> str:
    sections = [
        f"# task\n{_render_commands(document['context'])}",
        f"# diff\n{_render_commands([document['diff']])}",
        f"# preflight\n{_render_preflight(document['preflight'])}",
        *([] if document["rules"] is None else [f"# rules\n{_render_commands(document['rules'])}"]),
        "# grades\n" + "".join(f"{grade}\n" for grade in document["grades"]),
    ]
    return "\n".join(sections).removesuffix("\n")


def _decide_exit_code(document: dict) -> int:
    return 0


def verify_context(request, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime.paths.configuration_file)
    run_process = runtime.run_process
    project = require_project_at(
        read_projects(runtime), locate_main_checkout(run_process, locate_worktree_root(run_process, Path.cwd()))
    )
    found = find_opened_task(runtime, project.name, request.pr)
    demand = PreflightDemand(
        project=project,
        task=found.opened.task,
        wave_branch=found.wave_branch,
        pr=request.pr,
        forge=runtime.resolve_plugin("forge", FORGE_NAME),
        environment=read_forge_environment(configuration, CLI_KEY, runtime),
        configuration=configuration,
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **assemble_verify_context(runtime, demand)}


COMMAND = Command(
    path=("verify", "context"),
    help="print in one read what the verification of the pull request of a task judges",
    group_help="check the pull request of a task",
    arguments=(Argument(("pr",), {"type": int, "help": "the number of the pull request"}),),
    run=verify_context,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
