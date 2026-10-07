from brigade.command import Argument, Command

ROOT = ()
ROOT_METAVAR = "command"
GROUP_METAVAR = "action"
NO_HELP = None


def _name(path: tuple[str, ...]) -> str:
    return " ".join(("brigade", *path))


def _index_by_path(commands) -> dict[tuple[str, ...], Command]:
    by_path = {}
    for command in commands:
        if command.path in by_path:
            raise ValueError(f"two command records declare {_name(command.path)}")
        by_path[command.path] = command
    return by_path


def _declare_help(helps: dict, path: tuple[str, ...], help_text) -> None:
    if help_text is NO_HELP:
        return
    if helps.setdefault(path, help_text) != help_text:
        raise ValueError(f"two command records declare different helps for {_name(path)}")


def _collect_helps(commands) -> dict[tuple[str, ...], str]:
    helps = {}
    for command in commands:
        _declare_help(helps, command.path, command.help)
        _declare_help(helps, command.path[:-1], command.group_help)
    return helps


def _list_nodes(commands) -> list[tuple[str, ...]]:
    return sorted({command.path[:depth] for command in commands for depth in range(1, len(command.path) + 1)})


def _add_arguments(container, arguments) -> None:
    for argument in arguments:
        if isinstance(argument, Argument):
            container.add_argument(*argument.flags, **argument.settings)
        else:
            _add_arguments(container.add_mutually_exclusive_group(required=argument.required), argument.arguments)


def add_command_parsers(parser, commands, common_options) -> None:
    by_path = _index_by_path(commands)
    helps = _collect_helps(commands)
    parser.set_defaults(command=None)
    parsers = {ROOT: parser}
    actions = {ROOT: parser.add_subparsers(metavar=ROOT_METAVAR)}
    for node in _list_nodes(commands):
        parent = node[:-1]
        if parent not in actions:
            actions[parent] = parsers[parent].add_subparsers(metavar=GROUP_METAVAR, required=parent not in by_path)
        parsers[node] = actions[parent].add_parser(node[-1], parents=[common_options], help=helps.get(node))
        if node in by_path:
            _add_arguments(parsers[node], by_path[node].arguments)
            parsers[node].set_defaults(command=by_path[node])
