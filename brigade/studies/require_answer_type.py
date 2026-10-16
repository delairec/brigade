from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRequest

AWAWA_TIMEOUT_S = 30.0
DECLARED_EXIT_CODE = 0


def require_answer_type(runtime: Runtime, root: Path, answer_type: str) -> None:
    record = runtime.run_process(
        ProcessRequest(
            argv=("awawa", "show", answer_type, str(root)),
            cwd=str(root),
            timeout_s=AWAWA_TIMEOUT_S,
            acceptable_exit_codes=EVERY_EXIT_CODE,
        )
    )
    if record.exit_code != DECLARED_EXIT_CODE:
        raise BrigadeError(f"the schema of the operational corpus declares no {answer_type}")
