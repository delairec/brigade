import argparse

from brigade.command import Argument, Command
from brigade.commands._launch_planner import launch_planner
from brigade.runtime import Runtime
from brigade.triage.ratify_pattern import CONSTRAINT_KINDS, Ratification, ratify_pattern

DOCUMENT_SCHEMA_VERSION = 1


def _render_text(document: dict) -> str:
    ratified = f"@PATTERN.{document['pattern']} ratified: "
    if "order" in document:
        return ratified + f"@ORDER.{document['order']} active"
    placed = (
        f"@REQUEST.{document['request']} planning, run {document['run']}\nbrigade runs show {document['run']} --log"
    )
    if "constraint" in document:
        return ratified + f"@CONSTRAINT.{document['constraint']} proposed, " + placed
    return ratified + placed


def inbox_ratify(request: argparse.Namespace, runtime: Runtime) -> dict:
    ratified = ratify_pattern(runtime, Ratification(pattern=request.pattern, kind=request.kind))
    document = {"schema_version": DOCUMENT_SCHEMA_VERSION, **ratified.entities}
    if "request" not in document:
        return document
    return {**document, **launch_planner(runtime, ratified.project, document["request"])}


COMMAND = Command(
    path=("inbox", "ratify"),
    help="ratify a pattern by its action",
    arguments=(
        Argument(("pattern",), {"help": "the name of the PATTERN to ratify"}),
        Argument(
            ("--kind",),
            {"choices": CONSTRAINT_KINDS, "help": "the KIND of the CONSTRAINT a pattern of action constraint becomes"},
        ),
    ),
    run=inbox_ratify,
    render_text=_render_text,
)
