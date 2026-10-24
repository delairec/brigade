from collections.abc import Callable
from dataclasses import dataclass

from brigade.errors import ToolNotFound
from brigade.system.read_user_systemd_state import SYSTEMD_STATES_FIT_FOR_TIMERS, read_user_systemd_state
from brigade.system.run_process import ProcessRecord, ProcessRequest


@dataclass(frozen=True)
class SchedulerChoice:
    name: str
    chosen_by: str


def _probe_scheduler(run_process: Callable[[ProcessRequest], ProcessRecord]) -> str:
    try:
        systemd_state = read_user_systemd_state(run_process)
    except ToolNotFound:
        return "cron"
    return "systemd" if systemd_state in SYSTEMD_STATES_FIT_FOR_TIMERS else "cron"


def choose_scheduler(configured: str | None, run_process: Callable[[ProcessRequest], ProcessRecord]) -> SchedulerChoice:
    if configured is not None:
        return SchedulerChoice(name=configured, chosen_by="configuration")
    return SchedulerChoice(name=_probe_scheduler(run_process), chosen_by="probe")
