from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ForgeRequest:
    operation: str
    request: dict


class ForgeDouble:
    def __init__(self, answers: dict[str, Callable[[dict], object]]):
        self._answers = answers
        self.requests: list[ForgeRequest] = []

    def list_requests(self, operation: str) -> list[dict]:
        return [forge_request.request for forge_request in self.requests if forge_request.operation == operation]

    def __getattr__(self, operation: str) -> Callable[[dict, object], object]:
        answers = self.__dict__.get("_answers", {})
        if operation not in answers:
            raise AttributeError(operation)

        def answer(request: dict, runtime: object) -> object:
            self.requests.append(ForgeRequest(operation, request))
            return answers[operation](request)

        return answer
