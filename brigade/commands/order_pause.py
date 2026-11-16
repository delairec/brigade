import argparse

from brigade.command import Argument, Command
from brigade.commands._describe_order_status import describe_order_status
from brigade.orders.change_order_status import change_order_status
from brigade.runtime import Runtime

STATUS = "paused"


def _render_text(document: dict) -> str:
    return describe_order_status(document, "paused")


def order_pause(request: argparse.Namespace, runtime: Runtime) -> dict:
    return change_order_status(runtime, request.name, STATUS)


COMMAND = Command(
    path=("order", "pause"),
    help="pause an order, which the tick no longer runs",
    arguments=(Argument(("name",), {"help": "the name of the ORDER entity"}),),
    run=order_pause,
    render_text=_render_text,
)
