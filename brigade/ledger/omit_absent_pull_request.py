ABSENT_PULL_REQUEST = None


def omit_absent_pull_request(pr: int | None) -> dict:
    if pr is ABSENT_PULL_REQUEST:
        return {}
    return {"pr": pr}
