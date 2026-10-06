from dataclasses import dataclass
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Optional

from brigade.errors import BrigadeError
from brigade.roles.parse_role_file import RoleFileUnreadable, parse_role_file

INSTRUCTIONS_PROCEDURES_DIRECTORY = "procedures"
PROCEDURE_SUFFIX = ".md"
PATH_SEPARATOR = "/"
DECLARED_KEYS = ("capabilities", "budget")
CAPABILITIES = ("read", "write", "shell", "net")
CAPABILITY_SEPARATOR = ","


@dataclass(frozen=True)
class Procedure:
    name: str
    location: str
    argument: str
    capabilities: tuple[str, ...]
    budget: int
    body: str


@dataclass(frozen=True)
class ProcedureDirectories:
    shipped: Traversable
    instructions: Optional[str]


@dataclass(frozen=True)
class ProcedureSource:
    name: str
    location: str
    argument: str
    text: str


def _is_path(argument: str) -> bool:
    return PATH_SEPARATOR in argument or argument.endswith(PROCEDURE_SUFFIX)


def _read_path(argument: str) -> ProcedureSource:
    path = Path(argument).absolute()
    if not path.is_file():
        raise BrigadeError(f"no procedure file {path}")
    return ProcedureSource(
        name=path.stem, location=str(path), argument=str(path), text=path.read_text(encoding="utf-8")
    )


def _describe_missing(name: str, instructions: Optional[str]) -> str:
    if instructions is None:
        return f"no procedure {name}: not shipped with brigade and no instructions corpus set in config.toml"
    corpus_procedures = f"{instructions}/{INSTRUCTIONS_PROCEDURES_DIRECTORY}"
    return f"no procedure {name}: not shipped with brigade and not in {corpus_procedures}"


def _find_named(name: str, directories: ProcedureDirectories) -> ProcedureSource:
    instructions = directories.instructions
    shipped = directories.shipped / f"{name}{PROCEDURE_SUFFIX}"
    if shipped.is_file():
        return ProcedureSource(
            name=name, location=str(shipped), argument=name, text=shipped.read_text(encoding="utf-8")
        )
    if instructions is not None:
        corpus_file = Path(instructions) / INSTRUCTIONS_PROCEDURES_DIRECTORY / f"{name}{PROCEDURE_SUFFIX}"
        if corpus_file.is_file():
            return ProcedureSource(
                name=name, location=str(corpus_file), argument=name, text=corpus_file.read_text(encoding="utf-8")
            )
    raise BrigadeError(_describe_missing(name, instructions))


def _read_capabilities(value: str, location: str) -> tuple[str, ...]:
    capabilities = tuple(capability.strip() for capability in value.split(CAPABILITY_SEPARATOR) if capability.strip())
    outside = next((capability for capability in capabilities if capability not in CAPABILITIES), None)
    if outside is not None:
        raise BrigadeError(f"the procedure {location} declares {outside}, not one of {', '.join(CAPABILITIES)}")
    return capabilities


def _read_budget(value: str, location: str) -> int:
    if not (value.isascii() and value.isdigit() and int(value) > 0):
        raise BrigadeError(f"the procedure {location} has the budget {value}, not a positive integer")
    return int(value)


def resolve_procedure(argument: str, directories: ProcedureDirectories) -> Procedure:
    source = _read_path(argument) if _is_path(argument) else _find_named(argument, directories)
    try:
        procedure_file = parse_role_file(source.text)
    except RoleFileUnreadable as unreadable:
        raise BrigadeError(f"the procedure {source.location} {unreadable}") from None
    for key in DECLARED_KEYS:
        if key not in procedure_file.front_matter:
            raise BrigadeError(f"the procedure {source.location} lacks {key} in its front matter")
    return Procedure(
        name=source.name,
        location=source.location,
        argument=source.argument,
        capabilities=_read_capabilities(procedure_file.front_matter["capabilities"], source.location),
        budget=_read_budget(procedure_file.front_matter["budget"], source.location),
        body=procedure_file.body,
    )
