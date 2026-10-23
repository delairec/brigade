import argparse

from brigade.command import Command
from brigade.roles.resolve_role import NO_PROJECT_BINDINGS, resolve_role
from brigade.runtime import Runtime
from brigade.system.ask_named_client import ask_named_client
from brigade.system.client_question import ClientQuestion
from brigade.system.describe_client_answered import describe_client_answered
from brigade.system.describe_slot_clients import describe_slot_clients
from brigade.system.list_slot_clients_elsewhere import list_slot_clients_elsewhere
from brigade.system.probe_request import ProbeRequest
from brigade.system.read_configuration import SLOTS, Configuration
from brigade.system.read_optional_configuration import read_optional_configuration
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
NO_MODEL_BOUND = {}
COLUMNS = ("slot", "role", "source", "model")
NO_MODEL = "-"


def _read_bound_models(client_name: str | None, configuration: Configuration, runtime: Runtime) -> dict:
    if client_name is None:
        return NO_MODEL_BOUND
    client = runtime.resolve_plugin("client", client_name)
    question = ClientQuestion(client_name, ProbeRequest())
    return ask_named_client(client, question, configuration, runtime).models


def _render_row(row: dict) -> tuple[str, ...]:
    model = NO_MODEL if row["model"] is None else row["model"]
    return (row["slot"], row["role"], row["source"], model)


def _render_text(document: dict) -> str:
    return "\n".join(
        [
            render_table(COLUMNS, [_render_row(row) for row in document["roles"]]),
            describe_client_answered(document["client"]),
            *describe_slot_clients(document["slot_clients"]),
        ]
    )


def roles_list(request: argparse.Namespace, runtime: Runtime) -> dict:
    configuration = read_optional_configuration(runtime.paths.configuration_file)
    resolved_roles = [resolve_role(slot, runtime, NO_PROJECT_BINDINGS, configuration) for slot in SLOTS]
    slot_clients = list_slot_clients_elsewhere(configuration, configuration.client)
    models_by_client = {
        client_name: _read_bound_models(client_name, configuration, runtime)
        for client_name in dict.fromkeys([configuration.client, *slot_clients.values()])
    }
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "client": configuration.client,
        "slot_clients": slot_clients,
        "roles": [
            {
                "slot": resolved.slot,
                "role": resolved.role,
                "source": resolved.source,
                "model": models_by_client[slot_clients.get(resolved.slot, configuration.client)].get(
                    resolved.front_matter["reasoning"]
                ),
            }
            for resolved in resolved_roles
        ],
    }


COMMAND = Command(
    path=("roles", "list"),
    help="list the role, the source and the model of each slot",
    group_help="list, show and lint the roles each slot resolves to",
    run=roles_list,
    render_text=_render_text,
)
