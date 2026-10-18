from pathlib import Path

from brigade.commands._read_forge_environment import FORGE_NAME, read_forge_environment
from brigade.runtime import Runtime
from brigade.system.ask_pull_requests import PullRequestsQuery, ask_pull_requests
from brigade.system.read_configuration import CLI_KEY, Configuration


def read_pull_requests(repository: Path, state: str, configuration: Configuration, runtime: Runtime) -> list[dict]:
    query = PullRequestsQuery(
        repository=str(repository),
        state=state,
        environment=read_forge_environment(configuration, CLI_KEY, runtime),
    )
    return ask_pull_requests(runtime.resolve_plugin("forge", FORGE_NAME), FORGE_NAME, query, runtime)
