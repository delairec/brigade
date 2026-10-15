from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.read_configuration import Configuration
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRequest

NAME = "shell"
COMMAND_PARAMETER = "command"
SHELL = "sh"
SHELL_COMMAND_OPTION = "-c"
COMMAND_TIMEOUT_S = 600.0
COMPLETE_EXIT_CODE = 0
FRESH_AT_EACH_CALL = False


def collect(environment: dict, runtime: Runtime, configuration: Configuration) -> dict:
    inputs = read_collector_environment(environment)
    if COMMAND_PARAMETER not in inputs.parameters:
        raise BrigadeError(f"the shell collector takes {COMMAND_PARAMETER}=<line>")
    record = runtime.run_process(
        ProcessRequest(
            argv=(SHELL, SHELL_COMMAND_OPTION, inputs.parameters[COMMAND_PARAMETER]),
            cwd=str(inputs.project),
            timeout_s=COMMAND_TIMEOUT_S,
            acceptable_exit_codes=EVERY_EXIT_CODE,
        )
    )
    if record.exit_code != COMPLETE_EXIT_CODE:
        raise BrigadeError(f"the command exited {record.exit_code}\n{record.stderr.rstrip()}")
    lines = record.stdout.splitlines()
    return {**describe_collection(NAME, runtime, {"lines": len(lines)}, lines), "cache": FRESH_AT_EACH_CALL}
