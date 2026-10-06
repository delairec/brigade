from brigade.roles.resolve_role import NO_PROJECT_BINDINGS, resolve_role
from brigade.system.ask_configured_client import ask_configured_client
from brigade.system.read_configuration import SLOTS
from brigade.system.read_optional_configuration import read_optional_configuration

DOCUMENT_SCHEMA_VERSION = 1
CONFIGURATION_FILE = "config.toml"
NO_MODEL_BOUND = {}


def _read_bound_models(runtime) -> dict:
    configuration = read_optional_configuration(runtime.paths.config_root / CONFIGURATION_FILE)
    if configuration.client is None:
        return NO_MODEL_BOUND
    return ask_configured_client(runtime, "probe", {"schema_version": DOCUMENT_SCHEMA_VERSION}).document["models"]


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
