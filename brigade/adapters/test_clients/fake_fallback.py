from brigade.adapters.test_clients.answer_as_client import answer_as_client

CLIENT_NAME = "fake-fallback"


def answer(operation: str, request: dict) -> dict:
    return answer_as_client(CLIENT_NAME, operation, request)
