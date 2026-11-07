from dataclasses import dataclass

from brigade.runtime import Runtime


@dataclass(frozen=True)
class PullRequestTitles:
    forge: object
    repository: str
    environment: dict
    runtime: Runtime

    def read_title(self, number: int) -> str:
        request = {"repository": self.repository, "number": number, "environment": self.environment}
        return self.forge.read_pull_request(request, self.runtime)["pull_request"]["title"]
