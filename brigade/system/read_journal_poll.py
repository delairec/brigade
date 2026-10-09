from pathlib import Path

from brigade.system.name_toml_type import name_toml_type

JOURNAL_POLL_KEY = "journal_poll_s"
JOURNAL_POLL_BY_DEFAULT_S = 2


def _name_refused_value(value) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return name_toml_type(value)
    return str(value)


def read_journal_poll(document: dict, path: Path) -> tuple[int | float, tuple[str, ...]]:
    value = document.get(JOURNAL_POLL_KEY, JOURNAL_POLL_BY_DEFAULT_S)
    if not isinstance(value, bool) and isinstance(value, (int, float)) and value > 0:
        return value, ()
    finding = (
        f"{JOURNAL_POLL_KEY} is {_name_refused_value(value)}, not a positive number, in {path};"
        f" the default of {JOURNAL_POLL_BY_DEFAULT_S} s holds"
    )
    return JOURNAL_POLL_BY_DEFAULT_S, (finding,)
