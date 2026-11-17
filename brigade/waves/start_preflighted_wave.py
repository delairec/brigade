import sys
from collections.abc import Callable
from dataclasses import dataclass

from brigade.ledger.append_event import append_event
from brigade.ledger.wave_parked import WaveParked
from brigade.preflights.run_preflight import PreflightOutcome
from brigade.runtime import Runtime
from brigade.system.check_shapes import FAILED

FORGE_ACCOUNT_REASON = "forge_account"


@dataclass(frozen=True)
class PreflightedWaveStart:
    preflight: Callable[[], PreflightOutcome]
    start: Callable[[], dict]


def start_preflighted_wave(runtime: Runtime, demand: PreflightedWaveStart) -> dict:
    outcome = demand.preflight()
    started = demand.start()
    if outcome.result == FAILED:
        wave = started["wave"]
        append_event(runtime.paths, runtime.now, WaveParked(wave=wave, reason=FORGE_ACCOUNT_REASON))
        findings = "; ".join(finding for check in outcome.checks for finding in check["findings"])
        sys.stderr.write(
            f"brigade tick: the wave {wave} parked before any run: {findings};"
            f" repair the login, then run brigade wave resume {wave}\n"
        )
    return started
