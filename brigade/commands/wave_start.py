import argparse
import functools

from brigade.command import Argument, Command
from brigade.commands._read_cli_login import read_cli_login
from brigade.commands._read_forge_environment import read_forge_environment
from brigade.runtime import Runtime
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration
from brigade.waves.start_project_wave import WaveStart
from brigade.waves.start_project_waves import start_project_waves

DOCUMENT_SCHEMA_VERSION = 2


def _render_text(document: dict) -> str:
    return "\n".join(
        f"wave {wave['wave']} of @PROJECT.{wave['project']} on {wave['branch']}: {', '.join(wave['tasks'])}"
        for wave in document["waves"]
    )


def wave_start(request: argparse.Namespace, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime, CONFIGURATION_OPTIONAL)
    start = WaveStart(
        project=request.project,
        tasks=tuple(request.tasks),
        configuration=configuration,
        read_environment=functools.cache(lambda key: read_forge_environment(configuration, key, runtime)),
        read_login=functools.cache(lambda: read_cli_login(configuration, runtime)),
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "waves": list(start_project_waves(runtime, start))}


COMMAND = Command(
    path=("wave", "start"),
    help="compose a wave of the project's startable tasks per milestone and start each on its integration branch",
    group_help="start the waves of the projects, list, show and cancel them",
    arguments=(
        Argument(("project",), {"help": "the name of a registered PROJECT"}),
        Argument(
            ("--task",),
            {"action": "append", "default": [], "dest": "tasks", "help": "a task the wave takes, repeatable"},
        ),
    ),
    run=wave_start,
    render_text=_render_text,
)
