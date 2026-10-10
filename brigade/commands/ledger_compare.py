from dataclasses import asdict

from brigade.command import Argument, Command
from brigade.ledger.describe_comparison import describe_comparison
from brigade.ledger.describe_skipped_lines import describe_skipped_lines
from brigade.ledger.format_steps_lines import format_steps_lines
from brigade.ledger.read_ledger import read_ledger
from brigade.runtime import Runtime
from brigade.system.read_day import read_day

DOCUMENT_SCHEMA_VERSION = 1
MEASURE_LABELS = {
    "steps": "steps",
    "steps_to_first_edit": "steps to first edit",
    "oversized_output_steps": "oversized output steps",
}
STEPS_INDENT = "    "
NOT_REPORTED = "not reported"


def _render_measure(label: str, steps) -> list[str]:
    if steps is None:
        return [f"  {label}: {NOT_REPORTED}"]
    return [f"  {label}:", *format_steps_lines(STEPS_INDENT, steps)]


def _render_period(heading: str, period: dict) -> list[str]:
    return [
        f"{heading}: {period['runs']} runs finished, {period['segments']} segments",
        *(line for measure, label in MEASURE_LABELS.items() for line in _render_measure(label, period[measure])),
    ]


def _render_text(document: dict) -> str:
    day = document["before"]
    periods = document["periods"]
    return "\n".join(
        [*_render_period(f"before {day}", periods["before"]), *_render_period(f"from {day}", periods["from"])]
    )


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def ledger_compare(request, runtime: Runtime) -> dict:
    reading = read_ledger(runtime.paths.state_root)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        **describe_comparison(reading, request.before),
        "skipped": [asdict(line) for line in reading.skipped],
    }


COMMAND = Command(
    path=("ledger", "compare"),
    help="the runs before a day against the runs from that day on",
    arguments=(Argument(("--before",), {"type": read_day, "required": True, "help": "a day YYYY-MM-DD in UTC"}),),
    run=ledger_compare,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
    describe_diagnostics=describe_skipped_lines,
)
