from brigade.runtime import Runtime
from brigade.system.ask_named_client import ask_named_client
from brigade.system.client_question import ClientQuestion
from brigade.system.parse_configuration import Configuration
from brigade.system.probe_request import ProbeRequest


def read_attribution(configuration: Configuration, runtime: Runtime) -> list[str]:
    if configuration.attribution is not None:
        return list(configuration.attribution)
    if configuration.client is None:
        return []
    client = runtime.resolve_plugin("client", configuration.client)
    probe = ask_named_client(client, ClientQuestion(configuration.client, ProbeRequest()), configuration, runtime)
    return list(probe.attribution)
