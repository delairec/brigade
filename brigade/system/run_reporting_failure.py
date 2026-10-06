import sys
import traceback
from typing import Callable

from brigade.errors import BrigadeError


def run_reporting_failure(action: Callable[[], None], command: str) -> None:
    try:
        action()
    except BrigadeError as error:
        sys.stderr.write(f"brigade {command}: {error}\n")
    except Exception:
        traceback.print_exc()
