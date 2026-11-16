import argparse

from brigade.command import Argument, Command
from brigade.corpus.run_awawa import run_awawa
from brigade.orders.read_order_run import read_order_run
from brigade.recipes.find_answer_type import find_answer_type
from brigade.recipes.read_order_collected import read_order_collected
from brigade.recipes.render_result import render_result
from brigade.runtime import Runtime
from brigade.system.render_inline_json import render_inline_json

DOCUMENT_SCHEMA_VERSION = 1


def _render_collected(entry: dict) -> str:
    return f"{entry['collector']}: {render_inline_json(entry['summary'])}, {entry['document']}"


def _render_text(document: dict) -> str:
    head = [f"order: {document['order']}, run {document['run']}", *map(_render_collected, document["collected"])]
    return "\n\n".join(("\n".join(head), document["answer"].rstrip("\n"), document["schema"].rstrip("\n")))


def order_context(request: argparse.Namespace, runtime: Runtime) -> dict:
    run = read_order_run(runtime, request.run)
    root = runtime.paths.config_root
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "order": run.order,
        "run": run.run_id,
        "collected": read_order_collected(run),
        "answer": render_result(run),
        "schema": run_awawa(runtime.run_process, root, ("show", find_answer_type(run), str(root))).stdout,
    }


COMMAND = Command(
    path=("order", "context"),
    help="print the documents of a run of an order and the schema of the answer its judge step writes",
    arguments=(Argument(("run",), {"help": "the run of the order"}),),
    run=order_context,
    render_text=_render_text,
)
