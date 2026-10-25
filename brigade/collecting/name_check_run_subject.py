NO_PULL_REQUEST = None


def name_check_run_subject(check_run: dict) -> str:
    if check_run["pull_request"] is NO_PULL_REQUEST:
        return check_run["branch"]
    return str(check_run["pull_request"])
