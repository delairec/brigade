from pathlib import Path

CAUGHT_SIGNALS_FIELD = "SigCgt:"
HEXADECIMAL = 16


def is_catching_signal(pid: int, caught: int) -> bool:
    try:
        status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    except (FileNotFoundError, ProcessLookupError):
        return False
    mask = next(line for line in status.splitlines() if line.startswith(CAUGHT_SIGNALS_FIELD))
    caught_signals = int(mask.removeprefix(CAUGHT_SIGNALS_FIELD), HEXADECIMAL)
    return bool(caught_signals >> (caught - 1) & 1)
