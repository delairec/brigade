from dataclasses import dataclass

from brigade.runtime import Runtime
from brigade.system.ask_named_client import ask_named_client
from brigade.system.client_question import ClientQuestion, ClientRequest
from brigade.system.list_slot_clients_elsewhere import list_slot_clients_elsewhere
from brigade.system.require_configured_client import ConfiguredClient


@dataclass(frozen=True)
class ConfiguredClientAnswer:
    client: str
    slot_clients: dict
    document: dict


def ask_configured_client(
    client: object, configured: ConfiguredClient, request: ClientRequest, runtime: Runtime
) -> ConfiguredClientAnswer:
    answer = ask_named_client(client, ClientQuestion(configured.name, request), configured.configuration, runtime)
    return ConfiguredClientAnswer(
        client=configured.name,
        slot_clients=list_slot_clients_elsewhere(configured.configuration, configured.name),
        document=answer.to_document(),
    )
