from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.find_absence import find_absence
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.errors import BrigadeError
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.system.ask_pull_requests import PullRequestsQuery, ask_pull_requests
from brigade.system.read_account_environment import ForgeAccount, read_account_environment
from brigade.system.read_configuration import CLI_KEY
from brigade.tasks.locate_task_worktree import TASK_BRANCH

NAME = "pr-list"
STATE_PARAMETER = "state"
OPEN_STATE = "open"
COUNTED_STATES = ("open", "merged", "closed")
EVERY_STATE = "all"
ACCEPTED_STATES = (*COUNTED_STATES, EVERY_STATE)
FRESH_AT_EACH_CALL = False


def _read_state(parameters: dict) -> str:
    state = parameters.get(STATE_PARAMETER, OPEN_STATE)
    if state not in ACCEPTED_STATES:
        raise BrigadeError(f"the parameter state of {NAME} takes open, merged, closed or all, not {state}")
    return state


def _read_task(head: str) -> str | None:
    parts = TASK_BRANCH.fullmatch(head)
    if parts is None:
        return None
    return parts["task"]


def _read_pull_requests(inputs, equipment: CollectorEquipment, runtime: Runtime) -> list[dict]:
    account = ForgeAccount(forge=equipment.forge, forge_name=equipment.forge_name, key=CLI_KEY)
    query = PullRequestsQuery(
        repository=str(inputs.project),
        state=_read_state(inputs.parameters),
        environment=read_account_environment(account, equipment.configuration, runtime),
    )
    return ask_pull_requests(equipment.forge, equipment.forge_name, query, runtime)


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    project = require_project_at(read_projects(runtime), inputs.project)
    absence = find_absence(NAME, project)
    if absence is not None:
        raise BrigadeError(f"{NAME} is absent: {absence}")
    pull_requests = _read_pull_requests(inputs, equipment, runtime)
    items = [{**pull_request, "task": _read_task(pull_request["head"])} for pull_request in pull_requests]
    summary = {counted: sum(item["state"] == counted for item in items) for counted in COUNTED_STATES}
    return {**describe_collection(NAME, runtime, summary, items), "cache": FRESH_AT_EACH_CALL}
