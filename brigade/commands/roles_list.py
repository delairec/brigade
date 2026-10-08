from brigade.command import Command
from brigade.roles.resolve_role import NO_PROJECT_BINDINGS, resolve_role
from brigade.runtime import Runtime
from brigade.system.ask_client import ClientQuestion
from brigade.system.ask_named_client import ask_named_client
from brigade.system.read_configuration import SLOTS
from brigade.system.read_optional_configuration import read_optional_configuration
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
CONFIGURATION_FILE = "config.toml"
NO_MODEL_BOUND = {}
COLUMNS = ("slot", "role", "source", "model")
NO_MODEL = "-"


def _read_bound_models(runtime: Runtime) -> dict:
    configuration = read_optional_configuration(runtime.paths.config_root / CONFIGURATION_FILE)
    if configuration.client is None:
        return NO_MODEL_BOUND
    client = runtime.resolve_plugin("client", configuration.client)
    question = ClientQuestion(configuration.client, "probe", {"schema_version": DOCUMENT_SCHEMA_VERSION})
    return ask_named_client(client, question, configuration, runtime)["models"]


def _render_row(row: dict) -> tuple[str, ...]:
    model = NO_MODEL if row["model"] is None else row["model"]
    return (row["slot"], row["role"], row["source"], model)


def _render_text(document: dict) -> str:
    return render_table(COLUMNS, [_render_row(row) for row in document["roles"]])


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def roles_list(request, runtime: Runtime) -> dict:
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
