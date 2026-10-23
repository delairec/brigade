from dataclasses import asdict

from brigade.command import Argument, Command
from brigade.ledger.describe_budgets import describe_budgets
from brigade.ledger.describe_skipped_lines import describe_skipped_lines
from brigade.ledger.format_steps_lines import format_steps_lines
from brigade.ledger.read_ledger import read_ledger
from brigade.runtime import Runtime
from brigade.system.read_positive_count import read_positive_count

DOCUMENT_SCHEMA_VERSION = 1
LAST_RUNS_BY_DEFAULT = 20
ESTIMATE_MARK = "  estimate"
STEPS_INDENT = "    "


def _render_text(document: dict) -> str:
    procedures = document["procedures"]
    lines = [f"steps over the last {document['last']} runs finished of each procedure:"]
    for name, summary in procedures.items():
        lines.append(f"  {name}" + (ESTIMATE_MARK if summary["estimate"] else ""))
        lines.extend(format_steps_lines(STEPS_INDENT, summary))
    return "\n".join(lines)


def ledger_budgets(request, runtime: Runtime) -> dict:
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
    render_text=_render_text,
    describe_diagnostics=describe_skipped_lines,
)
