from pathlib import Path

from brigade.system.read_start_time import read_start_time

BOOT_ID_FILE = Path("/proc/sys/kernel/random/boot_id")


def read_process_identity(pid: int) -> str | None:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    boot_id = BOOT_ID_FILE.read_text(encoding="utf-8").strip()
    return f"{read_start_time(stat)} {boot_id}"
