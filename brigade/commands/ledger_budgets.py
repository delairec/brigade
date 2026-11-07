import argparse
from dataclasses import asdict

from brigade.command import Argument, Command
from brigade.ledger.describe_budgets import describe_budgets
from brigade.ledger.describe_role_budgets import describe_role_budgets
from brigade.ledger.describe_skipped_lines import describe_skipped_lines
from brigade.ledger.format_steps_lines import format_steps_lines
from brigade.ledger.read_ledger import read_ledger
from brigade.runtime import Runtime
from brigade.system.read_positive_count import read_positive_count

DOCUMENT_SCHEMA_VERSION = 1
LAST_RUNS_BY_DEFAULT = 20
ESTIMATE_MARK = "  estimate"
STEPS_INDENT = "    "
ABSENT = "-"
ROLES_HEADING = "step cap of each role at its latest digests:"


def _show_tokens(tokens: float | None) -> str:
    return ABSENT if tokens is None else str(round(tokens))


def _render_role(role: str, budget: dict) -> str:
    computed = ABSENT if budget["computed"] is None else budget["computed"]
    return (
        f"  {role}  shipped {budget['shipped']}  computed {computed}  applied {budget['applied']}"
        f"  segments {budget['segments']}  restarts {budget['restarts']}"
        f"  g {_show_tokens(budget['growth'])}  R {_show_tokens(budget['restart_tokens'])}"
    )


def _render_text(document: dict) -> str:
    procedures = document["procedures"]
    lines = [f"steps over the last {document['last']} runs finished of each procedure:"]
    for name, summary in procedures.items():
        lines.append(f"  {name}" + (ESTIMATE_MARK if summary["estimate"] else ""))
        lines.extend(format_steps_lines(STEPS_INDENT, summary))
    lines.append(ROLES_HEADING)
    lines.extend(_render_role(role, budget) for role, budget in document["roles"].items())
    return "\n".join(lines)


def ledger_budgets(request: argparse.Namespace, runtime: Runtime) -> dict:
    reading = read_ledger(runtime.paths.state_root)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        **describe_budgets(reading, request.last),
        "roles": describe_role_budgets(reading),
        "skipped": [asdict(line) for line in reading.skipped],
    }


COMMAND = Command(
    path=("ledger", "budgets"),
    help="p50 and p90 steps per procedure over its last runs, and the step cap of each role",
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
