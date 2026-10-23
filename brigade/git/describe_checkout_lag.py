from collections.abc import Callable
from pathlib import Path

from brigade.errors import ToolFailure
from brigade.git.read_upstream_lag import read_upstream_lag
from brigade.system.run_process import ProcessRecord, ProcessRequest


def describe_checkout_lag(run_process: Callable[[ProcessRequest], ProcessRecord], package_file: Path) -> str | None:
    checkout = package_file.resolve().parents[1]
    if not checkout.is_dir():
        return None
    try:
        lag = read_upstream_lag(run_process, checkout)
    except ToolFailure as error:
        return f"{checkout}: {error}"
    if lag is None:
        return None
    return f"{checkout} at {lag.commit}, {lag.behind} behind {lag.upstream} at {lag.upstream_commit}"
