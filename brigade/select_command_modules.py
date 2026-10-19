PASSTHROUGH_SEPARATOR = "--"
OPTION_PREFIX = "-"
MODULE_WORD_SEPARATOR = "_"


def _name_module(words: list[str]) -> str:
    return MODULE_WORD_SEPARATOR.join(words).replace("-", MODULE_WORD_SEPARATOR)


def _pick_module(words: list[str], module_names: list[str]) -> str | None:
    candidates = (_name_module(words[:length]) for length in range(len(words), 0, -1))
    return next((candidate for candidate in candidates if candidate in module_names), None)


def select_command_modules(arguments: list[str], module_names: list[str]) -> list[str]:
    separated = PASSTHROUGH_SEPARATOR in arguments
    command_line = arguments[: arguments.index(PASSTHROUGH_SEPARATOR)] if separated else arguments
    picked = _pick_module([word for word in command_line if not word.startswith(OPTION_PREFIX)], module_names)
    if picked is None:
        return []
    if not separated:
        return [picked]
    return [picked, *(name for name in module_names if name.startswith(f"{picked}{MODULE_WORD_SEPARATOR}"))]
