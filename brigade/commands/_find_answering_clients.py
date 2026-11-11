from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.ask_named_client import ask_named_client
from brigade.system.client_question import ClientQuestion
from brigade.system.list_client_adapters import SUPPORTED_CLIENT, list_client_adapters
from brigade.system.parse_configuration import Configuration
from brigade.system.probe_request import ProbeRequest
from brigade.system.run_process import ProcessRequest

PROBE_DIRECTORY = "/"
PROBE_TIMEOUT_S = 10.0
NO_CONFIGURATION = Configuration()


def _answers_its_probe(name: str, runtime: Runtime) -> bool:
    try:
        client = runtime.resolve_plugin("client", name)
        probe = ask_named_client(client, ClientQuestion(name, ProbeRequest()), NO_CONFIGURATION, runtime)
        if probe.version_argv is not None:
            runtime.run_process(ProcessRequest(argv=probe.version_argv, cwd=PROBE_DIRECTORY, timeout_s=PROBE_TIMEOUT_S))
    except BrigadeError:
        return False
    return True


def find_answering_clients(runtime: Runtime) -> tuple[str, ...]:
    return tuple(
        adapter.name
        for adapter in list_client_adapters(runtime)
        if adapter.audience == SUPPORTED_CLIENT and _answers_its_probe(adapter.name, runtime)
    )
