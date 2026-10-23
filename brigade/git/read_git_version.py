from collections.abc import Callable

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

PROBE_DIRECTORY = "/"


def read_git_version(run_process: Callable[[ProcessRequest], ProcessRecord]) -> str:
    record = run_process(ProcessRequest(argv=("git", "--version"), cwd=PROBE_DIRECTORY, timeout_s=GIT_TIMEOUT_S))
    return record.stdout.strip().removeprefix("git version ").partition(" ")[0]
