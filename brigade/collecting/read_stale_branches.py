from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.corpus.read_entities import Entity
from brigade.git.list_local_branches import list_local_branches
from brigade.registry.describe_remote import NO_FORGE
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.system.ask_pull_requests import PullRequestsQuery, ask_pull_requests
from brigade.system.parse_configuration import CLI_KEY
from brigade.system.read_account_environment import ForgeAccount, read_account_environment

EVERY_STATE = "all"
OPEN_STATE = "open"


def _read_pull_requests(repository: Path, equipment: CollectorEquipment, runtime: Runtime) -> list[dict]:
    account = ForgeAccount(forge=equipment.forge, forge_name=equipment.forge_name, key=CLI_KEY)
    query = PullRequestsQuery(
        repository=str(repository),
        state=EVERY_STATE,
        environment=read_account_environment(account, equipment.configuration, runtime),
    )
    return ask_pull_requests(equipment.forge, equipment.forge_name, query, runtime)


def read_stale_branches(project: Entity, equipment: CollectorEquipment, runtime: Runtime) -> list[dict]:
    if read_project_field(project, "FORGE") == NO_FORGE:
        return []
    repository = Path(read_project_field(project, "PATH"))
    main = read_project_field(project, "MAIN")
    branches = list_local_branches(runtime.run_process, repository)
    pull_requests = _read_pull_requests(repository, equipment, runtime)
    stale = []
    for branch in branches:
        own = [{"number": pr["number"], "state": pr["state"]} for pr in pull_requests if pr["head"] == branch]
        if branch != main and own and all(pr["state"] != OPEN_STATE for pr in own):
            stale.append({"branch": branch, "pull_requests": own})
    return stale
