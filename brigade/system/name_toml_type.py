import datetime

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


def name_toml_type(value: object) -> str:
    return next(name for kind, name in TOML_TYPE_NAMES if isinstance(value, kind))
