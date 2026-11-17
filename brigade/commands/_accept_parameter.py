PARAMETER_SEPARATOR = "="
OPTION_PREFIX = "-"


def accept_parameter(argument: str) -> bool:
    return PARAMETER_SEPARATOR in argument and not argument.startswith(OPTION_PREFIX)
