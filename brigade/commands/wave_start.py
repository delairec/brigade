import argparse
import functools

from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import read_forge_environment
from brigade.runtime import Runtime
from brigade.system.read_optional_configuration import read_optional_configuration
from brigade.waves.start_project_wave import WaveStart, start_project_wave

DOCUMENT_SCHEMA_VERSION = 1


def _render_text(document: dict) -> str:
    return (
        f"wave {document['wave']} of @PROJECT.{document['project']} on {document['branch']}:"
        f" {', '.join(document['tasks'])}"
    )


def wave_start(request: argparse.Namespace, runtime: Runtime) -> dict:
    configuration = read_optional_configuration(runtime.paths.configuration_file)
    start = WaveStart(
        project=request.project,
        tasks=tuple(request.tasks),
        configuration=configuration,
        read_environment=functools.cache(lambda key: read_forge_environment(configuration, key, runtime)),
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **start_project_wave(runtime, start)}


COMMAND = Command(
    path=("wave", "start"),
    help="compose a wave of the project's startable tasks and start it on its integration branch",
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
