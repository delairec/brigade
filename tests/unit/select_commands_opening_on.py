from brigade.system.run_process import ProcessRequest


def select_commands_opening_on(requests: list[ProcessRequest], prefix: tuple[str, ...]) -> list[tuple]:
    return [(request.cwd, request.argv) for request in requests if request.argv[: len(prefix)] == prefix]
