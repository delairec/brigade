from collections.abc import Callable, Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Argument:
    flags: tuple[str, ...]
    settings: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ExclusiveArguments:
    arguments: tuple[Argument, ...]
    required: bool = False


def _describe_no_diagnostics(document) -> list[str]:
    return []


def _select_whole_result(result):
    return result


def _read_the_options(options):
    return options


def _exit_0(document) -> int:
    return 0


@dataclass(frozen=True)
class Command:
    path: tuple[str, ...]
    help: str
    run: Callable[[object, object], object]
    render_text: Callable[[object], str]
    read_request: Callable[[object], object] = _read_the_options
    decide_exit_code: Callable[[object], int] = _exit_0
    arguments: tuple[Argument | ExclusiveArguments, ...] = ()
    group_help: str | None = None
    describe_diagnostics: Callable[[object], list[str]] = _describe_no_diagnostics
    render_markdown: Callable[[dict], str] | None = None
    accept_extra_argument: Callable[[str], bool] | None = None
    render_passed_stderr: Callable[[object], str] | None = None
    select_document: Callable[[object], object] = _select_whole_result
