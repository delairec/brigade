def omit_absent_pull_request(pr: int | None) -> dict:
    if pr is None:
        return {}
    return {"pr": pr}
