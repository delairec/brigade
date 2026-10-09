from collections.abc import Callable

from brigade.system.poll_until_signalled import poll_until_signalled

NOT_DONE = False


def repeat_until_signalled(action: Callable[[], None], interval_s: float) -> int:
    repetitions = 0

    def _perform_once() -> bool:
        nonlocal repetitions
        action()
        repetitions += 1
        return NOT_DONE

    poll_until_signalled(_perform_once, interval_s)
    return repetitions
