from dataclasses import dataclass
from typing import Optional

from brigade.errors import BrigadeError

KIND_NAMES = {bool: "boolean", int: "integer", float: "number", str: "string", list: "list", dict: "object"}
NULL_NAME = "null"
NAMES_TAKING_AN = ("integer", "object")


class DocumentInvalid(BrigadeError):
    pass


@dataclass(frozen=True)
class Field:
    kinds: tuple
    nullable: bool = False
    values: tuple | None = None
    fields: dict | None = None
    items: Optional["Field"] = None
    non_empty: bool = False
    optional: bool = False


def _name_value_kind(value) -> str:
    if value is None:
        return NULL_NAME
    return KIND_NAMES[type(value)]


def _articulate(kind_name: str) -> str:
    if kind_name == NULL_NAME:
        return kind_name
    article = "an" if kind_name in NAMES_TAKING_AN else "a"
    return f"{article} {kind_name}"


def _fits_kind(value, kinds: tuple) -> bool:
    if isinstance(value, bool):
        return bool in kinds
    return isinstance(value, kinds)


def _check_object(document: dict, fields: dict, prefix: str) -> None:
    for key, field in fields.items():
        location = f"{prefix}{key}"
        if key in document:
            _check_value(document[key], field, location)
        elif not field.optional:
            raise DocumentInvalid(f"lacks the key {location}")


def _check_value(value, field: Field, location: str) -> None:
    if value is None and field.nullable:
        return
    if value is None or not _fits_kind(value, field.kinds):
        expected = " or ".join(_articulate(KIND_NAMES[kind]) for kind in field.kinds)
        raise DocumentInvalid(f"{location} is {_articulate(_name_value_kind(value))}, not {expected}")
    if field.values is not None and value not in field.values:
        allowed = ", ".join(str(allowed_value) for allowed_value in field.values)
        raise DocumentInvalid(f"{location} is {value!r}, not one of {allowed}")
    if field.non_empty and not value:
        raise DocumentInvalid(f"{location} is an empty list")
    if field.fields is not None:
        _check_object(value, field.fields, f"{location}.")
    if field.items is not None:
        for index, item in enumerate(value):
            _check_value(item, field.items, f"{location}[{index}]")


def validate_document(document: object, shape: dict) -> None:
    if not isinstance(document, dict):
        raise DocumentInvalid(f"the document is {_articulate(_name_value_kind(document))}, not an object")
    _check_object(document, shape, "")
