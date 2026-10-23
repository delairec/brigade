from dataclasses import dataclass

from brigade.system.parse_configuration import REASONING_LEVELS, SLOTS

DECLARED_KEYS = ("name", "slot", "work", "reasoning", "capabilities", "budget", "returns")
CAPABILITIES = ("read", "write", "shell", "net")
MODEL_KEY = "model"
CAPABILITY_SEPARATOR = ","


@dataclass(frozen=True)
class RoleProblem:
    key: str
    problem: str


def _describe_outside(value: str, allowed: tuple[str, ...]) -> str:
    return f"is {value}, not one of {', '.join(allowed)}"


def _check_value(key: str, value: str):
    if key == MODEL_KEY:
        return "names a model"
    if key not in DECLARED_KEYS:
        return "is not a declared key"
    if not value:
        return "is empty"
    if key == "reasoning" and value not in REASONING_LEVELS:
        return _describe_outside(value, REASONING_LEVELS)
    if key == "slot" and value not in SLOTS:
        return _describe_outside(value, SLOTS)
    if key == "capabilities":
        capabilities = [capability.strip() for capability in value.split(CAPABILITY_SEPARATOR)]
        outside = next((capability for capability in capabilities if capability not in CAPABILITIES), None)
        if outside is not None:
            return _describe_outside(outside, CAPABILITIES)
    if key == "budget" and not (value.isascii() and value.isdigit() and int(value) > 0):
        return f"is {value}, not a positive integer"
    return None


def check_front_matter(front_matter: dict) -> tuple[RoleProblem, ...]:
    value_problems = [(key, _check_value(key, value)) for key, value in front_matter.items()]
    missing = [(key, "is missing") for key in DECLARED_KEYS if key not in front_matter]
    return tuple(
        RoleProblem(key=key, problem=problem) for key, problem in [*value_problems, *missing] if problem is not None
    )
