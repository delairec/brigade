import argparse

from brigade.command import Argument, Command
from brigade.roles.render_role_file import render_role_file
from brigade.roles.resolve_role import NO_PROJECT_BINDINGS, resolve_role
from brigade.runtime import Runtime
from brigade.system.parse_configuration import SLOTS
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration

DOCUMENT_SCHEMA_VERSION = 1
FINAL_NEWLINE = "\n"
NO_BODY = ""


def _render_text(document: dict) -> str:
    if "body" in document:
        return render_role_file(document["front_matter"], document["body"]).removesuffix(FINAL_NEWLINE)
    front_matter_block = render_role_file(document["front_matter"], NO_BODY)
    return (
        f"{front_matter_block}body: {document['body_lines']} lines, {document['body_bytes']} bytes,"
        f" source {document['source']}"
    )


def roles_show(request: argparse.Namespace, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime, CONFIGURATION_OPTIONAL)
    resolved = resolve_role(request.slot, runtime, NO_PROJECT_BINDINGS, configuration)
    identity = {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "slot": resolved.slot,
        "role": resolved.role,
        "source": resolved.source,
        "front_matter": resolved.front_matter,
    }
    if request.short:
        return {
            **identity,
            "body_lines": len(resolved.body.splitlines()),
            "body_bytes": len(resolved.body.encode("utf-8")),
        }
    return {**identity, "body": resolved.body}


COMMAND = Command(
    path=("roles", "show"),
    help="print the role file a slot resolves to",
    group_help="list, show and lint the roles each slot resolves to",
    arguments=(
        Argument(("slot",), {"choices": SLOTS}),
        Argument(("--short",), {"action": "store_true", "help": "print the front matter and the size of the body"}),
    ),
    run=roles_show,
    render_text=_render_text,
)
