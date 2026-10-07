from brigade.command import Command
from brigade.roles.resolve_role import NO_PROJECT_BINDINGS, resolve_role
from brigade.system.ask_configured_client import ask_configured_client
from brigade.system.read_configuration import SLOTS
from brigade.system.read_optional_configuration import read_optional_configuration

DOCUMENT_SCHEMA_VERSION = 1
CONFIGURATION_FILE = "config.toml"
NO_MODEL_BOUND = {}
SLOT_WIDTH = 9
ROLE_WIDTH = 12
SOURCE_WIDTH = 14
HEADER = {"slot": "slot", "role": "role", "source": "source", "model": "model"}
NO_MODEL = "-"


def _read_bound_models(runtime) -> dict:
    configuration = read_optional_configuration(runtime.paths.config_root / CONFIGURATION_FILE)
    if configuration.client is None:
        return NO_MODEL_BOUND
    return ask_configured_client(runtime, "probe", {"schema_version": DOCUMENT_SCHEMA_VERSION}).document["models"]


def _render_row(row: dict) -> str:
    model = NO_MODEL if row["model"] is None else row["model"]
    return f"{row['slot']:<{SLOT_WIDTH}}{row['role']:<{ROLE_WIDTH}}{row['source']:<{SOURCE_WIDTH}}{model}"


def _render_text(document: dict) -> str:
    return "\n".join(_render_row(row) for row in [HEADER, *document["roles"]])


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def roles_list(request, runtime) -> dict:
    resolved_roles = [resolve_role(slot, runtime, NO_PROJECT_BINDINGS) for slot in SLOTS]
    models = _read_bound_models(runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "roles": [
            {
                "slot": resolved.slot,
                "role": resolved.role,
                "source": resolved.source,
                "model": models.get(resolved.front_matter["reasoning"]),
            }
            for resolved in resolved_roles
        ],
    }


COMMAND = Command(
    path=("roles", "list"),
    help="list the role, the source and the model of each slot",
    group_help="list, show and lint the roles each slot resolves to",
    run=roles_list,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
