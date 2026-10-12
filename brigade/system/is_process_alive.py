import os

NO_SIGNAL = 0


def is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, NO_SIGNAL)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
