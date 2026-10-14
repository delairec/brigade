def describe_skipped_runs(skipped: list[dict]) -> list[str]:
    return [f"run {run['run']} skipped, {run['reason']}" for run in skipped]
