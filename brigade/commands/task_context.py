from pathlib import Path

from brigade.command import Argument, Command
from brigade.runtime import Runtime
from brigade.system.ask_named_client import ask_named_client
from brigade.system.client_question import ClientQuestion
from brigade.system.probe_request import ProbeRequest
from brigade.system.read_configuration import Configuration, read_configuration
from brigade.system.write_text_atomically import write_text_atomically
from brigade.tasks.assemble_task_context import assemble_task_context
from brigade.tasks.locate_task_worktree import locate_task_worktree

DOCUMENT_SCHEMA_VERSION = 1
PACKAGE_FILE = "context.md"
HEAVY_MARK = "  (left to CI)"


def _render_lines(lines: list[str]) -> str:
    return "".join(f"{line}\n" for line in lines)


def _render_commands(entries: list[dict]) -> str:
    return "".join(
        f"$ {entry['command']}\nexit {entry['exit_code']}\n{entry['stderr']}{entry['output']}" for entry in entries
    )


def _render_worktree(worktree: dict) -> str:
    ancestry = worktree["ancestry"]
    setup = worktree["setup"] or ""
    return f"# worktree\n$ {ancestry['command']}\nexit {ancestry['exit_code']}\n{setup}"


def _render_reserved(reserved: dict) -> str:
    temporary_directory = reserved["temporary_directory"]
    return _render_lines(
        [
            "# reserved",
            f"task number {reserved['task_number']}",
            *reserved["attribution"],
            *([] if temporary_directory is None else [f"temporary directory {temporary_directory}"]),
        ]
    )


def _render_text(document: dict) -> str:
    acceptance = document["acceptance"]
    sections = [
        _render_worktree(document["worktree"]),
        f"# task\n{_render_commands(document['task'])}",
        *([] if document["rules"] is None else [f"# rules\n{_render_commands(document['rules'])}"]),
        *([] if document["project"] is None else [f"# project\n{document['project']}"]),
        _render_lines(
            ["# acceptance", *acceptance["acceptance"], *(f"{command}{HEAVY_MARK}" for command in acceptance["heavy"])]
        ),
        _render_reserved(document["reserved"]),
        _render_lines(["# when done", *document["when_done"]]),
    ]
    return "\n".join(sections).removesuffix("\n")


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def _read_attribution(configuration: Configuration, runtime: Runtime) -> list[str]:
    if configuration.attribution is not None:
        return list(configuration.attribution)
    if configuration.client is None:
        return []
    client = runtime.resolve_plugin("client", configuration.client)
    probe = ask_named_client(client, ClientQuestion(configuration.client, ProbeRequest()), configuration, runtime)
    return list(probe.attribution)


def task_context(request, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime.paths.configuration_file)
    worktree = locate_task_worktree(runtime, Path.cwd(), request.task)
    document = {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        **assemble_task_context(runtime, configuration, worktree, _read_attribution(configuration, runtime)),
    }
    if runtime.paths.run_directory is not None:
        write_text_atomically(runtime.paths.run_directory / PACKAGE_FILE, f"{_render_text(document)}\n")
    return document


COMMAND = Command(
    path=("task", "context"),
    help="print the starting package of a build run in the worktree of its task",
    group_help="work on a task of a wave from its worktree",
    arguments=(Argument(("task",), {"nargs": "?"}),),
    run=task_context,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
