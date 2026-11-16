PARAMETER_SEPARATOR = "="


def read_parameters(arguments: list[str]) -> dict:
    return dict(argument.split(PARAMETER_SEPARATOR, 1) for argument in arguments)
