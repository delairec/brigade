from brigade.adapters.test_clients import fake

CLIENT_NAME = "fake-fallback"


def answer(operation: str, request: dict) -> dict:
    document = fake.answer(operation, request)
    if operation == "probe":
        return {**document, "client": CLIENT_NAME}
    return document
