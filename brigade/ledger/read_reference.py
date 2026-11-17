import argparse

REFERENCE_MEASURES = ("turns_to_first_edit_p50", "task_run_turns_p50", "oversized_output_turns_per_launch")
FIGURE_SEPARATOR = "="


def _read_figure(text: str) -> float:
    try:
        return float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a number") from None


def read_reference(text: str) -> tuple[str, float]:
    measure, _, figure = text.partition(FIGURE_SEPARATOR)
    if measure not in REFERENCE_MEASURES:
        raise argparse.ArgumentTypeError(f"{measure!r} is not a reference measure: {', '.join(REFERENCE_MEASURES)}")
    return measure, _read_figure(figure)
