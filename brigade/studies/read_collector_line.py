from brigade.system.split_command import split_command

SHELL_PREFIX = "shell:"
SHELL_COLLECTOR = "shell"
SHELL_COMMAND_PARAMETER = "command"
PARAMETER_SEPARATOR = "="


def read_collector_line(line: str) -> tuple[str, dict]:
    if line.startswith(SHELL_PREFIX):
        command = line.removeprefix(SHELL_PREFIX).strip()
        split_command(command)
        return SHELL_COLLECTOR, {SHELL_COMMAND_PARAMETER: command}
    name, *parameters = line.split()
    return name, dict(parameter.split(PARAMETER_SEPARATOR, 1) for parameter in parameters)
