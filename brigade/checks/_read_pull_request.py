PULL_REQUEST_COLLECTOR = "pull-request"


def read_pull_request(subject: dict) -> dict:
    return subject["collected"][PULL_REQUEST_COLLECTOR]["summary"]
