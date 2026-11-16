import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.decode_atom import decode_atom
from brigade.corpus.run_awawa import run_awawa
from brigade.preflights.name_preflight_entity import name_preflight_entity
from brigade.system.run_process import ProcessRecord, ProcessRequest

ENTITY_TYPE = "PREFLIGHT"
SHOWN = 0
NOT_SHOWN = 1
PREFLIGHT_SCHEMA_VERSION = 1
PARAMETER_SEPARATOR = "="


def _decode(field: dict) -> str:
    return "".join(map(decode_atom, field["atoms"]))


def _read_steps(fields: list[dict], field_name: str) -> list[dict]:
    return [
        {
            "name": _decode(field),
            "parameters": dict(_decode(parameter).split(PARAMETER_SEPARATOR, 1) for parameter in field["fields"]),
        }
        for field in fields
        if field["name"] == field_name
    ]


def _read_title(fields: list[dict]) -> str:
    return next(_decode(field) for field in fields if field["name"] == "TITLE")


@dataclass(frozen=True)
class PreflightEntity:
    preflight: dict
    file: Path


def locate_preflight_entity(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, name: str
) -> PreflightEntity | None:
    target = f"@{ENTITY_TYPE}.{name_preflight_entity(name)}"
    record = run_awawa(run_process, root, ("show", target, "--json", str(root)), (SHOWN, NOT_SHOWN))
    if record.exit_code == NOT_SHOWN:
        return None
    shown = json.loads(record.stdout)
    fields = shown["fields"]
    preflight = {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "name": name,
        "description": _read_title(fields),
        "collectors": _read_steps(fields, "COLLECTOR"),
        "checks": _read_steps(fields, "CHECK"),
    }
    return PreflightEntity(preflight=preflight, file=Path(shown["file"]))


def read_preflight_entity(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, name: str) -> dict | None:
    entity = locate_preflight_entity(run_process, root, name)
    return None if entity is None else entity.preflight
