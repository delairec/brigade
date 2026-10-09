from brigade.errors import ToolFailure, ToolNotFound
from brigade.system.process_trace import NO_WORKING_DIRECTORY, NOT_FOUND


def explain_launch_failure(argv: tuple[str, ...], cwd: str, missing: FileNotFoundError) -> tuple[str, ToolFailure]:
    if missing.filename == cwd:
        return NO_WORKING_DIRECTORY, ToolFailure(f"{argv[0]}: no working directory {cwd}")
    return NOT_FOUND, ToolNotFound(f"{argv[0]} not on PATH")
