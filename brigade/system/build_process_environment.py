from collections.abc import Mapping

INHERITED_VARIABLES = ("PATH", "HOME", "LANG")
INHERITED_PREFIXES = ("LC_", "XDG_", "BRIGADE_")


def build_process_environment(environment: Mapping[str, str]) -> dict[str, str]:
    return {
        name: value
        for name, value in environment.items()
        if name in INHERITED_VARIABLES or name.startswith(INHERITED_PREFIXES)
    }
