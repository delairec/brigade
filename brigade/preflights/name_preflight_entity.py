NAME_WORD_SEPARATOR = "-"
ENTITY_WORD_SEPARATOR = "_"


def name_preflight_entity(name: str) -> str:
    return name.replace(NAME_WORD_SEPARATOR, ENTITY_WORD_SEPARATOR)
