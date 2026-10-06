from dataclasses import dataclass
from typing import Callable, Optional

from brigade.system.run_process import ProcessRecord, ProcessRequest

PROBE_DIRECTORY = "/"
PROBE_TIMEOUT_S = 10.0
KEY_PRESENT_OR_ABSENT = (0, 1)
KEY_ABSENT = 1


@dataclass(frozen=True)
class GitIdentity:
    name: Optional[str]
    email: Optional[str]


def _read_key(run_process: Callable[[ProcessRequest], ProcessRecord], key: str) -> Optional[str]:
    record = run_process(
        ProcessRequest(
            argv=("git", "config", "--get", key),
            cwd=PROBE_DIRECTORY,
            timeout_s=PROBE_TIMEOUT_S,
            acceptable_exit_codes=KEY_PRESENT_OR_ABSENT,
        )
    )
    value = record.stdout.strip()
    if record.exit_code == KEY_ABSENT or not value:
        return None
    return value


def read_git_identity(run_process: Callable[[ProcessRequest], ProcessRecord]) -> GitIdentity:
    return GitIdentity(name=_read_key(run_process, "user.name"), email=_read_key(run_process, "user.email"))
