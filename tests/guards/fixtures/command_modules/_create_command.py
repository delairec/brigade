from brigade.command import Command


def _run(request, runtime) -> dict:
    return {"schema_version": 1}


def _keep(options):
    return options


def _render(document) -> str:
    return ""


def _decide_done(document) -> int:
    return 0


def create_command(path: tuple[str, ...], *, passthrough: bool) -> Command:
    return Command(
        path=path,
        help="a command line of the fixture",
        run=_run,
        read_request=_keep,
        render_text=_render,
        decide_exit_code=_decide_done,
        render_passed_stderr=_render if passthrough else None,
    )
