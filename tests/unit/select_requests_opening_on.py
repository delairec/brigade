from brigade.system.run_process import ProcessRequest


def select_requests_opening_on(requests: list[ProcessRequest], *prefixes: tuple[str, ...]) -> list[ProcessRequest]:
    return [request for request in requests if any(request.argv[: len(prefix)] == prefix for prefix in prefixes)]
