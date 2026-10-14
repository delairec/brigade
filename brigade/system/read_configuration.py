import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.name_toml_type import name_toml_type
from brigade.system.read_journal_poll import JOURNAL_POLL_BY_DEFAULT_S, JOURNAL_POLL_KEY, read_journal_poll
from brigade.system.read_trail_days import TRAIL_DAYS_BY_DEFAULT, TRAIL_DAYS_KEY, read_trail_days

STRING_KEYS = ("client", "scheduler", "instructions", "document")
DOCUMENT_BY_DEFAULT = "awawa"
UNREAD_STRING_KEYS = ("ide_link",)
REFS_CACHE_MB_KEY = "refs_cache_mb"
REASONING_LEVELS = ("deepest", "deep", "standard", "light")
REASONING_ROW_KEYS = ("model", "effort")
SECONDS_PER_STEP_KEY = "seconds_per_step"
SECONDS_PER_STEP_BY_DEFAULT = 30
SOFT_LIMIT_MARGIN_KEY = "soft_limit_margin_s"
SOFT_LIMIT_MARGIN_BY_DEFAULT_S = 120
SLOTS = ("plan", "build", "review", "remediate", "rebase", "report", "triage", "rules", "explore")
CLI_KEY = "cli"
FORGE_ACCOUNTS_KEY = "forge_accounts"
FORGE_ACCOUNT_KEYS = (*SLOTS, CLI_KEY)
FORGE_ATTEMPTS_KEY = "forge_attempts"
FORGE_ATTEMPTS_BY_DEFAULT = 3
FEWEST_FORGE_ATTEMPTS = 1


class ConfigurationMissing(BrigadeError):
    pass


@dataclass(frozen=True)
class ReasoningRow:
    model: str
    effort: str


@dataclass(frozen=True)
class Configuration:
    client: str | None = None
    scheduler: str | None = None
    instructions: str | None = None
    document: str = DOCUMENT_BY_DEFAULT
    refs_cache_mb: int = 1024
    reasoning: dict = field(default_factory=dict)
    clients: dict = field(default_factory=dict)
    slots: dict = field(default_factory=dict)
    seconds_per_step: int | float = SECONDS_PER_STEP_BY_DEFAULT
    soft_limit_margin_s: int | float = SOFT_LIMIT_MARGIN_BY_DEFAULT_S
    trail_days: int = TRAIL_DAYS_BY_DEFAULT
    journal_poll_s: int | float = JOURNAL_POLL_BY_DEFAULT_S
    findings: tuple[str, ...] = ()
    forge_accounts: dict = field(default_factory=dict)
    forge_attempts: int = FORGE_ATTEMPTS_BY_DEFAULT


def _require(value, kind: type, expected: str, location: str, path: Path):
    if not isinstance(value, kind):
        raise BrigadeError(f"{location} is {name_toml_type(value)}, not {expected}, in {path}")
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


def _read_forge_accounts(table, path: Path) -> dict:
    _require(table, dict, "a table", FORGE_ACCOUNTS_KEY, path)
    _refuse_unknown_keys(table, FORGE_ACCOUNT_KEYS, f"{FORGE_ACCOUNTS_KEY}.", path)
    return {key: _require(login, str, "a string", f"{FORGE_ACCOUNTS_KEY}.{key}", path) for key, login in table.items()}


def _read_forge_attempts(document: dict, path: Path) -> int:
    value = document.get(FORGE_ATTEMPTS_KEY, FORGE_ATTEMPTS_BY_DEFAULT)
    if isinstance(value, bool) or not isinstance(value, int):
        raise BrigadeError(f"{FORGE_ATTEMPTS_KEY} is {name_toml_type(value)}, not an integer, in {path}")
    if value < FEWEST_FORGE_ATTEMPTS:
        raise BrigadeError(f"{FORGE_ATTEMPTS_KEY} is {value}, not {FEWEST_FORGE_ATTEMPTS} or more, in {path}")
    return value


def _read_refs_cache_mb(document: dict, path: Path) -> int:
    value = document.get(REFS_CACHE_MB_KEY, Configuration.refs_cache_mb)
    if isinstance(value, bool) or not isinstance(value, int):
        raise BrigadeError(f"{REFS_CACHE_MB_KEY} is {name_toml_type(value)}, not an integer, in {path}")
    if value < 0:
        raise BrigadeError(f"{REFS_CACHE_MB_KEY} is {value}, not 0 or more, in {path}")
    return value


def _read_positive_number(document: dict, key: str, default: int, path: Path) -> int | float:
    value = document.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BrigadeError(f"{key} is {name_toml_type(value)}, not a number, in {path}")
    if value <= 0:
        raise BrigadeError(f"{key} is {value}, not a positive number, in {path}")
    return value


def _parse(path: Path) -> dict:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ConfigurationMissing(f"no configuration at {path}; run brigade init") from None
    try:
        return tomllib.loads(content)
    except tomllib.TOMLDecodeError as error:
        raise BrigadeError(f"{path} is not valid TOML: {error}") from None


def read_configuration(path: Path) -> Configuration:
    document = _parse(path)
    _refuse_unknown_keys(
        document,
        (
            *STRING_KEYS,
            *UNREAD_STRING_KEYS,
            REFS_CACHE_MB_KEY,
            "reasoning",
            "clients",
            "slots",
            SECONDS_PER_STEP_KEY,
            SOFT_LIMIT_MARGIN_KEY,
            TRAIL_DAYS_KEY,
            JOURNAL_POLL_KEY,
            FORGE_ACCOUNTS_KEY,
            FORGE_ATTEMPTS_KEY,
        ),
        "",
        path,
    )
    for key in UNREAD_STRING_KEYS:
        if key in document:
            _require(document[key], str, "a string", key, path)
    strings = {key: _require(document[key], str, "a string", key, path) for key in STRING_KEYS if key in document}
    journal_poll_s, findings = read_journal_poll(document, path)
    return Configuration(
        **strings,
        refs_cache_mb=_read_refs_cache_mb(document, path),
        reasoning=_read_reasoning(document.get("reasoning", {}), path),
        clients=_read_clients(document.get("clients", {}), path),
        slots=_read_slots(document.get("slots", {}), path),
        seconds_per_step=_read_positive_number(document, SECONDS_PER_STEP_KEY, SECONDS_PER_STEP_BY_DEFAULT, path),
        soft_limit_margin_s=_read_positive_number(
            document, SOFT_LIMIT_MARGIN_KEY, SOFT_LIMIT_MARGIN_BY_DEFAULT_S, path
        ),
        trail_days=read_trail_days(document, path),
        journal_poll_s=journal_poll_s,
        findings=findings,
        forge_accounts=_read_forge_accounts(document.get(FORGE_ACCOUNTS_KEY, {}), path),
        forge_attempts=_read_forge_attempts(document, path),
    )
