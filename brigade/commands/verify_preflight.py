from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import FORGE_NAME, read_forge_environment
from brigade.runtime import Runtime
from brigade.system.read_configuration import read_configuration
from brigade.verify.preflight_pull_request import PreflightDemand, preflight_pull_request

CLI_KEY = "cli"
FAILED = "fail"


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    lines = [f"preflight of #{document['pr']}, @TASK.{document['task']} at {document['head']}"]
    for check in document["checks"]:
        lines.append(f"{check['verdict']}  {check['name']}")
        lines.extend(f"  {finding}" for finding in check["findings"])
    return "\n".join(lines)


def _decide_exit_code(document: dict) -> int:
    return int(any(check["verdict"] == FAILED for check in document["checks"]))


def verify_preflight(request, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime.paths.configuration_file)
    return preflight_pull_request(
        runtime,
        PreflightDemand(
            path=Path.cwd(),
            pr=request.pr,
            forge=runtime.resolve_plugin("forge", FORGE_NAME),
            environment=read_forge_environment(configuration, CLI_KEY, runtime),
            configuration=configuration,
        ),
    )


COMMAND = Command(
    path=("verify", "preflight"),
    help="run the deterministic checks of a pull request of a task before any judgment",
    group_help="check the pull request of a task",
    arguments=(Argument(("pr",), {"type": int, "help": "the number of the pull request"}),),
    run=verify_preflight,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
