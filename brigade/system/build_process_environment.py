import os

INHERITED_VARIABLES = ("PATH", "HOME", "LANG", "COVERAGE_PROCESS_CONFIG")
INHERITED_PREFIXES = ("LC_", "XDG_", "BRIGADE_")


def build_process_environment() -> dict[str, str]:
    return {
        name: value
        for name, value in os.environ.items()
        if name in INHERITED_VARIABLES or name.startswith(INHERITED_PREFIXES)
    }
