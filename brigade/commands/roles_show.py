from brigade.command import Argument, Command
from brigade.roles.render_role_file import render_role_file
from brigade.roles.resolve_role import NO_PROJECT_BINDINGS, resolve_role
from brigade.runtime import Runtime
from brigade.system.read_configuration import SLOTS
from brigade.system.read_optional_configuration import read_optional_configuration

DOCUMENT_SCHEMA_VERSION = 1
FINAL_NEWLINE = "\n"


def _render_text(document: dict) -> str:
    return render_role_file(document["front_matter"], document["body"]).removesuffix(FINAL_NEWLINE)


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def roles_show(request, runtime: Runtime) -> dict:
    configuration = read_optional_configuration(runtime.paths.configuration_file)
    resolved = resolve_role(request.slot, runtime, NO_PROJECT_BINDINGS, configuration)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "slot": resolved.slot,
        "role": resolved.role,
        "source": resolved.source,
        "front_matter": resolved.front_matter,
        "body": resolved.body,
    }


COMMAND = Command(
    path=("roles", "show"),
    help="print the role file a slot resolves to",
    group_help="list, show and lint the roles each slot resolves to",
    arguments=(Argument(("slot",), {"choices": SLOTS}),),
    run=roles_show,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
