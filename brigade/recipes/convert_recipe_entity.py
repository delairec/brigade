from brigade.corpus.decode_atom import decode_atom

DOCUMENT_KEYS = {"SCHEMA_VERSION": "schema_version", "DESC": "description", "MAX_WALL": "max_wall"}
INTEGER_FIELDS = ("SCHEMA_VERSION", "MAX_WALL")
PARAM_FIELD = "PARAM"
STEP_FIELD = "STEP"
ARGV_FIELD = "ARGV"
PARAMETER_FIELD = "PARAMETER"
PARAMETER_SEPARATOR = "="


def _read_value(field: dict) -> str:
    return "".join(map(decode_atom, field["atoms"]))


def _read_document_value(field: dict) -> str | int:
    value = _read_value(field)
    return int(value) if field["name"] in INTEGER_FIELDS else value


def _convert_step(step: dict) -> dict:
    converted = {"kind": _read_value(step)}
    for field in step["fields"]:
        value = _read_value(field)
        if field["name"] == ARGV_FIELD:
            converted.setdefault("argv", []).append(value)
        elif field["name"] == PARAMETER_FIELD:
            key, _, parameter = value.partition(PARAMETER_SEPARATOR)
            converted.setdefault("parameters", {})[key] = parameter
        else:
            converted[field["name"].lower()] = value
    return converted


def convert_recipe_entity(shown: dict) -> dict:
    fields = shown["fields"]
    return {
        "name": shown["name"],
        **{
            DOCUMENT_KEYS[field["name"]]: _read_document_value(field)
            for field in fields
            if field["name"] in DOCUMENT_KEYS
        },
        "params": [_read_value(field) for field in fields if field["name"] == PARAM_FIELD],
        "steps": [_convert_step(field) for field in fields if field["name"] == STEP_FIELD],
    }
