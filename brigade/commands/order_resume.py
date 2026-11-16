import argparse

from brigade.command import Argument, Command
from brigade.commands._describe_order_status import describe_order_status
from brigade.orders.change_order_status import change_order_status
from brigade.orders.find_parked_order_run import NO_PARKED_RUN
from brigade.orders.relaunch_parked_order_run import relaunch_parked_order_run
from brigade.runtime import Runtime

STATUS = "active"


def _render_text(document: dict) -> str:
    head = describe_order_status(document, "resumed")
    if document["run"] is NO_PARKED_RUN:
        return head
    return f"{head}; run {document['run']} relaunched"


def order_resume(request: argparse.Namespace, runtime: Runtime) -> dict:
    document = change_order_status(runtime, request.name, STATUS)
    return {**document, "run": relaunch_parked_order_run(runtime, request.name)}


COMMAND = Command(
    path=("order", "resume"),
    help="resume a paused order, which the tick runs again when due, and relaunch its parked run at its first undone"
    " step",
    arguments=(Argument(("name",), {"help": "the name of the ORDER entity"}),),
    run=order_resume,
    render_text=_render_text,
)
