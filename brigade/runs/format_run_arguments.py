ABSENT = "-"


def format_run_arguments(arguments: dict) -> str:
    return " ".join(f"{name}={value}" for name, value in sorted(arguments.items())) or ABSENT
