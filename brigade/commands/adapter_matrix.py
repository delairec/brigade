from brigade.errors import BrigadeError
from brigade.system.ask_client import ClientQuestion
from brigade.system.ask_named_client import ask_named_client
from brigade.system.list_client_adapters import SUPPORTED_CLIENT, ClientAdapter, list_client_adapters
from brigade.system.read_configuration import Configuration
from brigade.system.read_optional_configuration import read_optional_configuration

SCHEMA_VERSION = 1
CONFIGURATION_FILE = "config.toml"
PROBE_OPERATION = "probe"
PROBE_REQUEST = {"schema_version": 1}
OPERATION_CAPABILITIES = ("launch", "result", "resume", "transcripts")
FEATURE_CAPABILITIES = ("step_count", "tool_grants", "reset_hour")
CAPABILITIES = OPERATION_CAPABILITIES + FEATURE_CAPABILITIES
FALLBACKS = {
    "resume": "a fresh launch from the progress file",
    "transcripts": "brigade's own run logs",
    "step_count": "steps null and the run held on the clock alone",
    "tool_grants": "the client's unattended mode and a disposable worktree for a reading slot",
    "reset_hour": "now plus thirty minutes",
}
FULL = "full"
FALLBACK = "fallback"
ABSENT = "absent"
NO_ERROR = None
NO_CAPABILITIES = None


def _grade(capability: str, declared: list[str]) -> str:
    if capability in declared:
        return FULL
    if capability in FALLBACKS:
        return FALLBACK
    return ABSENT


def _grade_capabilities(probe: dict) -> dict:
    return {
        **{capability: _grade(capability, probe["operations"]) for capability in OPERATION_CAPABILITIES},
        **{capability: _grade(capability, probe["features"]) for capability in FEATURE_CAPABILITIES},
    }


def _describe_adapter(runtime, configuration: Configuration, adapter: ClientAdapter) -> dict:
    row = {"name": adapter.name, "audience": adapter.audience}
    try:
        probe = ask_named_client(runtime, configuration, ClientQuestion(adapter.name, PROBE_OPERATION, PROBE_REQUEST))
    except BrigadeError as error:
        return {**row, "capabilities": NO_CAPABILITIES, "error": str(error)}
    return {**row, "capabilities": _grade_capabilities(probe), "error": NO_ERROR}


def _order_row(row: dict) -> tuple[bool, str]:
    return row["audience"] != SUPPORTED_CLIENT, row["name"]


def adapter_matrix(request, runtime) -> dict:
    configuration = read_optional_configuration(runtime.paths.config_root / CONFIGURATION_FILE)
    rows = [_describe_adapter(runtime, configuration, adapter) for adapter in list_client_adapters(runtime)]
    return {"schema_version": SCHEMA_VERSION, "adapters": sorted(rows, key=_order_row), "fallbacks": FALLBACKS}
