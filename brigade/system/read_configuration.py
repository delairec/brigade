import datetime
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from brigade.errors import BrigadeError

STRING_KEYS = ("client", "scheduler", "forge_account", "instructions", "ide_link")
REFS_CACHE_MB_KEY = "refs_cache_mb"
REASONING_LEVELS = ("deepest", "deep", "standard", "light")
REASONING_ROW_KEYS = ("model", "effort")
SECONDS_PER_STEP_KEY = "seconds_per_step"
SECONDS_PER_STEP_BY_DEFAULT = 30
SLOTS = ("plan", "build", "verify", "review", "rebase", "report", "triage", "rules", "explore")
TOML_TYPE_NAMES = (
    (bool, "a boolean"),
    (int, "an integer"),
    (float, "a number"),
    (str, "a string"),
    (dict, "a table"),
    (list, "an array"),
    (datetime.date, "a date"),
    (datetime.time, "a date"),
)


@dataclass(frozen=True)
class ReasoningRow:
    model: str
    effort: str


@dataclass(frozen=True)
class Configuration:
    client: Optional[str] = None
    scheduler: Optional[str] = None
    forge_account: Optional[str] = None
    instructions: Optional[str] = None
    ide_link: Optional[str] = None
    refs_cache_mb: int = 1024
    reasoning: dict = field(default_factory=dict)
    clients: dict = field(default_factory=dict)
    slots: dict = field(default_factory=dict)
    seconds_per_step: int | float = SECONDS_PER_STEP_BY_DEFAULT


def _name_toml_type(value) -> str:
    return next(name for kind, name in TOML_TYPE_NAMES if isinstance(value, kind))


def _require(value, kind: type, expected: str, location: str, path: Path):
    if not isinstance(value, kind):
        raise BrigadeError(f"{location} is {_name_toml_type(value)}, not {expected}, in {path}")
    return value


def _refuse_unknown_keys(table: dict, known_keys: tuple, prefix: str, path: Path) -> None:
    for key in table:
        if key not in known_keys:
            raise BrigadeError(f"unknown key {prefix}{key} in {path}")


def _read_reasoning_row(row, level: str, path: Path) -> ReasoningRow:
    location = f"reasoning.{level}"
    _require(row, dict, "a table", location, path)
    _refuse_unknown_keys(row, REASONING_ROW_KEYS, f"{location}.", path)
    for key in REASONING_ROW_KEYS:
        if key not in row:
            raise BrigadeError(f"{location} lacks {key} in {path}")
        _require(row[key], str, "a string", f"{location}.{key}", path)
    return ReasoningRow(model=row["model"], effort=row["effort"])


def _read_reasoning(table, path: Path) -> dict:
    _require(table, dict, "a table", "reasoning", path)
    _refuse_unknown_keys(table, REASONING_LEVELS, "reasoning.", path)
    return {level: _read_reasoning_row(row, level, path) for level, row in table.items()}


def _read_client_settings(settings, name: str, path: Path) -> dict:
    location = f"clients.{name}"
    _require(settings, dict, "a table", location, path)
    for key, value in settings.items():
        _require(value, str, "a string", f"{location}.{key}", path)
    return dict(settings)


def _read_clients(table, path: Path) -> dict:
    _require(table, dict, "a table", "clients", path)
    return {name: _read_client_settings(settings, name, path) for name, settings in table.items()}


def _read_slots(table, path: Path) -> dict:
    _require(table, dict, "a table", "slots", path)
    _refuse_unknown_keys(table, SLOTS, "slots.", path)
    return {slot: _require(name, str, "a string", f"slots.{slot}", path) for slot, name in table.items()}


def _read_refs_cache_mb(document: dict, path: Path) -> int:
    value = document.get(REFS_CACHE_MB_KEY, Configuration.refs_cache_mb)
    if isinstance(value, bool) or not isinstance(value, int):
        raise BrigadeError(f"{REFS_CACHE_MB_KEY} is {_name_toml_type(value)}, not an integer, in {path}")
    if value < 0:
        raise BrigadeError(f"{REFS_CACHE_MB_KEY} is {value}, not 0 or more, in {path}")
    return value


def _read_seconds_per_step(value, path: Path) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BrigadeError(f"{SECONDS_PER_STEP_KEY} is {_name_toml_type(value)}, not a number, in {path}")
    if value <= 0:
        raise BrigadeError(f"{SECONDS_PER_STEP_KEY} is {value}, not a positive number, in {path}")
    return value


def _parse(path: Path) -> dict:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise BrigadeError(f"no configuration at {path}; run brigade init") from None
    try:
        return tomllib.loads(content)
    except tomllib.TOMLDecodeError as error:
        raise BrigadeError(f"{path} is not valid TOML: {error}") from None


def read_configuration(path: Path) -> Configuration:
    document = _parse(path)
    _refuse_unknown_keys(
        document, (*STRING_KEYS, REFS_CACHE_MB_KEY, "reasoning", "clients", "slots", SECONDS_PER_STEP_KEY), "", path
    )
    strings = {key: _require(document[key], str, "a string", key, path) for key in STRING_KEYS if key in document}
    return Configuration(
        **strings,
        refs_cache_mb=_read_refs_cache_mb(document, path),
        reasoning=_read_reasoning(document.get("reasoning", {}), path),
        clients=_read_clients(document.get("clients", {}), path),
        slots=_read_slots(document.get("slots", {}), path),
        seconds_per_step=_read_seconds_per_step(
            document.get(SECONDS_PER_STEP_KEY, SECONDS_PER_STEP_BY_DEFAULT), path
        ),
    )
