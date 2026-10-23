from dataclasses import dataclass

from brigade.runtime import Runtime
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
    return parse_configuration(path)
