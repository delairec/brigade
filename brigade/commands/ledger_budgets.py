from dataclasses import asdict

from brigade.command import Argument, Command
from brigade.ledger.describe_budgets import describe_budgets
from brigade.ledger.describe_skipped_lines import describe_skipped_lines
from brigade.ledger.format_steps_line import format_steps_line
from brigade.ledger.read_ledger import read_ledger
from brigade.system.read_positive_count import read_positive_count

DOCUMENT_SCHEMA_VERSION = 1
LAST_RUNS_BY_DEFAULT = 20
ESTIMATE_MARK = "  estimate"


def _render_text(document: dict) -> str:
    procedures = document["procedures"]
    width = max((len(name) for name in procedures), default=0)
    lines = [f"steps over the last {document['last']} runs finished of each procedure:"]
    for name, summary in procedures.items():
        lines.append(format_steps_line(name, width, summary) + (ESTIMATE_MARK if summary["estimate"] else ""))
    return "\n".join(lines)


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def ledger_budgets(request, runtime) -> dict:
    reading = read_ledger(runtime.paths.state_root)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        **describe_budgets(reading, request.last),
        "skipped": [asdict(line) for line in reading.skipped],
    }


COMMAND = Command(
    path=("ledger", "budgets"),
    help="p50 and p90 steps per procedure over its last runs",
    arguments=(
        Argument(
            ("--last",),
            {
                "type": read_positive_count,
                "default": LAST_RUNS_BY_DEFAULT,
                "help": "the runs of each procedure, 20 by default",
            },
        ),
    ),
    run=ledger_budgets,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
    describe_diagnostics=describe_skipped_lines,
)
