from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.list_client_adapters import list_client_adapters
from brigade.system.parse_configuration import Configuration, parse_configuration


@dataclass(frozen=True)
class ConfigurationRequest:
    required: bool


CONFIGURATION_REQUIRED = ConfigurationRequest(required=True)
CONFIGURATION_OPTIONAL = ConfigurationRequest(required=False)


NOTHING_CONFIGURED = Configuration()


def read_configuration(runtime: Runtime, request: ConfigurationRequest) -> Configuration:
    path = runtime.paths.configuration_file
    if not request.required and not path.exists():
        return NOTHING_CONFIGURED
    configuration = parse_configuration(path)
    _refuse_a_fallback_found_nowhere(configuration, runtime)
    return configuration


def _refuse_a_fallback_found_nowhere(configuration: Configuration, runtime: Runtime) -> None:
    if configuration.fallback is None:
        return
    client = configuration.fallback.client
    if client not in {adapter.name for adapter in list_client_adapters(runtime)}:
        raise BrigadeError(
            f"fallback.client names {client}, a client adapter found nowhere, in {runtime.paths.configuration_file}"
        )
