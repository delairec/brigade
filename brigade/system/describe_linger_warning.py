from collections.abc import Callable

from brigade.errors import ToolFailure, ToolNotFound
from brigade.system.run_process import ProcessRecord, ProcessRequest

LINGERING = "Linger=yes"
NO_LINGER = "no linger: the timer stops at logout; run loginctl enable-linger"
PROBE_DIRECTORY = "/"
PROBE_TIMEOUT_S = 10.0


def describe_linger_warning(run_process: Callable[[ProcessRequest], ProcessRecord]) -> str | None:
    request = ProcessRequest(
        argv=("loginctl", "show-user", "-p", "Linger"), cwd=PROBE_DIRECTORY, timeout_s=PROBE_TIMEOUT_S
    )
    try:
        record = run_process(request)
    except ToolNotFound:
        return "loginctl not on PATH"
    except ToolFailure as error:
        return str(error)
    return None if record.stdout.strip() == LINGERING else NO_LINGER
