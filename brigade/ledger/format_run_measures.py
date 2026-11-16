from brigade.ledger.format_duration import format_duration

ABSENT = "-"


def _show_steps(run: dict) -> str:
    steps = ABSENT if run["steps"] is None else str(run["steps"])
    return f"{steps} partial" if run["partial"] else steps


def _show_duration(milliseconds: int | None) -> str:
    return ABSENT if milliseconds is None else format_duration(milliseconds)


def _show_cost(cost_usd: float | None) -> str:
    return ABSENT if cost_usd is None else f"{cost_usd:.2f} USD"


def format_run_measures(run: dict) -> str:
    return (
        f"steps {_show_steps(run)}  duration {_show_duration(run['duration_ms'])}  cost {_show_cost(run['cost_usd'])}"
    )
