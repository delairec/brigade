from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.read_configuration import Configuration
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRequest
from brigade.system.split_command import split_command

NAME = "shell"
COMMAND_PARAMETER = "command"
NO_COMMAND = ""
COMMAND_TIMEOUT_S = 600.0
COMPLETE_EXIT_CODE = 0
FRESH_AT_EACH_CALL = False


def collect(environment: dict, runtime: Runtime, configuration: Configuration) -> dict:
    inputs = read_collector_environment(environment)
    argv = split_command(inputs.parameters.get(COMMAND_PARAMETER, NO_COMMAND))
    if not argv:
        raise BrigadeError(f"the shell collector takes {COMMAND_PARAMETER}=<line>")
    record = runtime.run_process(
        ProcessRequest(
            argv=argv,
            cwd=str(inputs.project),
            timeout_s=COMMAND_TIMEOUT_S,
            acceptable_exit_codes=EVERY_EXIT_CODE,
        )
    )
    if record.exit_code != COMPLETE_EXIT_CODE:
        raise BrigadeError(f"the command exited {record.exit_code}\n{record.stderr.rstrip()}")
    lines = record.stdout.splitlines()
    return {**describe_collection(NAME, runtime, {"lines": len(lines)}, lines), "cache": FRESH_AT_EACH_CALL}
