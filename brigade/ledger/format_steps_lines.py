NO_PERCENTILE = "-"


def _show_percentile(value) -> str:
    return NO_PERCENTILE if value is None else str(value)


def _show_percentiles(summary: dict) -> str:
    return f"p50 {_show_percentile(summary['p50'])}  p90 {_show_percentile(summary['p90'])}"


def _format_runs_line(indent: str, runs: dict) -> str:
    counts = f"measured {runs['measured']}  partial {runs['partial']}  unmeasured {runs['unmeasured']}"
    return f"{indent}runs {_show_percentiles(runs)}  {counts}"


def _format_segments_line(indent: str, segments: dict) -> str:
    counts = f"measured {segments['measured']}  unmeasured {segments['unmeasured']}"
    return f"{indent}segments {_show_percentiles(segments)}  {counts}"


def format_steps_lines(indent: str, steps: dict) -> list[str]:
    return [_format_runs_line(indent, steps["runs"]), _format_segments_line(indent, steps["segments"])]
