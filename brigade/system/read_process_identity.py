from pathlib import Path

from brigade.system.identify_process import identify_process


def _read_kernel_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_process_identity(pid: int) -> str | None:
    return identify_process(pid, _read_kernel_file)
