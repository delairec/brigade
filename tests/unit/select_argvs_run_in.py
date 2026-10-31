from brigade.system.run_process import ProcessRequest


def select_argvs_run_in(requests: list[ProcessRequest], cwd: str) -> list[tuple[str, ...]]:
    return [request.argv for request in requests if request.cwd == cwd]
