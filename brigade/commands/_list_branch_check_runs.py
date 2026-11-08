import functools
from collections.abc import Callable

from brigade.commands._read_forge_environment import FORGE_KIND, FORGE_NAME, read_forge_environment
from brigade.runtime import Runtime
from brigade.system.ask_check_runs import CheckRunsQuery, ask_check_runs
from brigade.system.parse_configuration import CLI_KEY, Configuration


def list_branch_check_runs(runtime: Runtime, configuration: Configuration) -> Callable[[str, str], list[dict]]:
    read_environment = functools.cache(lambda key: read_forge_environment(configuration, key, runtime))
    return lambda repository, branch: ask_check_runs(
        runtime.resolve_plugin(FORGE_KIND, FORGE_NAME),
        FORGE_NAME,
        CheckRunsQuery(repository=repository, branch=branch, environment=read_environment(CLI_KEY)),
        runtime,
    )
