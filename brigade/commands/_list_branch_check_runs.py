import functools
from collections.abc import Callable

from brigade.commands._read_forge_environment import FORGE_KIND, ForgeSlot, read_forge_environment
from brigade.registry.read_project_forge import NO_FORGE
from brigade.runtime import Runtime
from brigade.system.ask_check_runs import CheckRunsQuery, ask_check_runs
from brigade.system.parse_configuration import CLI_KEY, Configuration

NO_CHECK_RUN = []


def list_branch_check_runs(
    runtime: Runtime, configuration: Configuration, forge_name: str
) -> Callable[[str, str], list[dict]]:
    if forge_name == NO_FORGE:
        return lambda repository, branch: NO_CHECK_RUN
    read_environment = functools.cache(
        lambda key: read_forge_environment(configuration, ForgeSlot(forge_name, key), runtime)
    )
    return lambda repository, branch: ask_check_runs(
        runtime.resolve_plugin(FORGE_KIND, forge_name),
        forge_name,
        CheckRunsQuery(repository=repository, branch=branch, environment=read_environment(CLI_KEY)),
        runtime,
    )
