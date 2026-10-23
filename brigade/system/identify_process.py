from collections.abc import Callable
from pathlib import Path

from brigade.system.read_start_time import read_start_time

BOOT_ID_FILE = Path("/proc/sys/kernel/random/boot_id")


def identify_process(pid: int, read_kernel_file: Callable[[Path], str]) -> str | None:
    try:
        stat = read_kernel_file(Path(f"/proc/{pid}/stat"))
    except (FileNotFoundError, ProcessLookupError):
        return None
    boot_id = read_kernel_file(BOOT_ID_FILE).strip()
    return f"{read_start_time(stat)} {boot_id}"
