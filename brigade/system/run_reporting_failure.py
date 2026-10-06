import sys
import traceback
from collections.abc import Callable

from brigade.errors import BrigadeError


def run_reporting_failure(action: Callable[[], None], command: str) -> None:
    try:
        action()
    except BrigadeError as error:
        sys.stderr.write(f"brigade {command}: {error}\n")
    except Exception:  # noqa: BLE001 - one failed tick of the loop: the traceback is printed, the next tick runs
        traceback.print_exc()
