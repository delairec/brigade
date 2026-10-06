from typing import Callable

from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRecord, ProcessRequest

SYSTEMD_STATES_FIT_FOR_TIMERS = ("running", "degraded")
PROBE_DIRECTORY = "/"
PROBE_TIMEOUT_S = 10.0


def read_user_systemd_state(run_process: Callable[[ProcessRequest], ProcessRecord]) -> str:
    record = run_process(
        ProcessRequest(
            argv=("systemctl", "--user", "is-system-running"),
            cwd=PROBE_DIRECTORY,
            timeout_s=PROBE_TIMEOUT_S,
            acceptable_exit_codes=EVERY_EXIT_CODE,
        )
    )
    return record.stdout.strip().partition("\n")[0]
