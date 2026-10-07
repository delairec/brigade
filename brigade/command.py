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


@dataclass(frozen=True)
class Command:
    path: tuple[str, ...]
    help: str
    run: Callable[[object, object], object]
    read_request: Callable[[object], object]
    render_text: Callable[[object], str]
    decide_exit_code: Callable[[object], int]
    arguments: tuple[Argument | ExclusiveArguments, ...] = ()
    group_help: str | None = None
    describe_diagnostics: Callable[[object], list[str]] = _describe_no_diagnostics
    render_markdown: Callable[[dict], str] | None = None
    accept_extra_argument: Callable[[str], bool] | None = None
    render_passed_stderr: Callable[[object], str] | None = None
