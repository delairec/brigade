NO_PERCENTILE = "-"


def _show_percentile(value) -> str:
    return NO_PERCENTILE if value is None else str(value)


def format_steps_line(name: str, width: int, summary: dict) -> str:
    return (
        f"  {name:<{width}}  p50 {_show_percentile(summary['p50'])}  p90 {_show_percentile(summary['p90'])}"
        f"  measured {summary['measured']}  unmeasured {summary['unmeasured']}"
    )
