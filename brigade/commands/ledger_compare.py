import argparse
from dataclasses import asdict

from brigade.command import Argument, Command
from brigade.errors import UsageError
from brigade.ledger.describe_comparison import describe_comparison
from brigade.ledger.describe_skipped_lines import describe_skipped_lines
from brigade.ledger.format_steps_lines import format_steps_lines
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.read_reference import read_reference
from brigade.runtime import Runtime
from brigade.system.read_day_range import read_day_range

DOCUMENT_SCHEMA_VERSION = 1
MEASURE_LABELS = {
    "steps": "steps",
    "steps_to_first_edit": "steps to first edit",
    "oversized_output_steps": "oversized output steps",
}
FIGURE_LABELS = {
    "steps_to_first_edit_p50": "steps to first edit p50",
    "task_run_steps_p50": "steps per task run p50",
    "oversized_output_steps_per_launch": "oversized output steps per launch",
}
STEPS_INDENT = "    "
NOT_REPORTED = "not reported"
ABSENT = "-"
COMPARED_RANGES = 2
RANGE_AGAINST_REFERENCE = 1


def _render_measure(label: str, steps) -> list[str]:
    if steps is None:
        return [f"  {label}: {NOT_REPORTED}"]
    return [f"  {label}:", *format_steps_lines(STEPS_INDENT, steps)]


def _show_figure(figure: float | None) -> str:
    return ABSENT if figure is None else f"{figure:g}"


def _render_figures(figures: dict) -> list[str]:
    return [f"  {FIGURE_LABELS[measure]}: {_show_figure(figure)}" for measure, figure in figures.items()]


def _render_range(day_range: dict) -> list[str]:
    return [
        (
            f"from {day_range['start']} to {day_range['end']}:"
            f" {day_range['runs']} runs finished, {day_range['segments']} segments"
        ),
        *(line for measure, label in MEASURE_LABELS.items() for line in _render_measure(label, day_range[measure])),
        *_render_figures(day_range["figures"]),
    ]


def _render_reference(reference: dict) -> list[str]:
    if not reference:
        return []
    return ["reference:", *_render_figures(reference)]


def _render_text(document: dict) -> str:
    return "\n".join(
        [
            *(line for day_range in document["ranges"] for line in _render_range(day_range)),
            *_render_reference(document["reference"]),
        ]
    )


def _read_reference_figures(references: list[tuple[str, float]]) -> dict:
    measures = [measure for measure, _ in references]
    repeated = sorted({measure for measure in measures if measures.count(measure) > 1})
    if repeated:
        raise UsageError(f"compare takes one --reference per measure: {', '.join(repeated)}")
    return dict(references)


def _read_request(options: argparse.Namespace) -> argparse.Namespace:
    reference = _read_reference_figures(options.reference or [])
    expected_ranges = RANGE_AGAINST_REFERENCE if reference else COMPARED_RANGES
    if len(options.range) != expected_ranges:
        raise UsageError("compare takes two --range, or one --range and --reference")
    return argparse.Namespace(ranges=tuple(options.range), reference=reference)


def ledger_compare(request: argparse.Namespace, runtime: Runtime) -> dict:
    reading = read_ledger(runtime.paths.state_root)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        **describe_comparison(reading, request.ranges, request.reference),
        "skipped": [asdict(line) for line in reading.skipped],
    }


COMMAND = Command(
    path=("ledger", "compare"),
    help="two ranges of days against each other, or one range against reference figures",
    arguments=(
        Argument(
            ("--range",),
            {
                "type": read_day_range,
                "action": "append",
                "required": True,
                "metavar": "START..END",
                "help": "the runs finished from the day START to the day END included, YYYY-MM-DD in UTC",
            },
        ),
        Argument(
            ("--reference",),
            {
                "type": read_reference,
                "action": "append",
                "metavar": "MEASURE=VALUE",
                "help": "a reference figure the one range is compared with, repeatable",
            },
        ),
    ),
    run=ledger_compare,
    read_request=_read_request,
    render_text=_render_text,
    describe_diagnostics=describe_skipped_lines,
)
