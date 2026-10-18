from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.find_absence import find_absence
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.commands._read_pull_requests import read_pull_requests
from brigade.errors import BrigadeError
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.system.read_configuration import Configuration
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


def collect(environment: dict, runtime: Runtime, configuration: Configuration) -> dict:
    inputs = read_collector_environment(environment)
    project = require_project_at(read_projects(runtime), inputs.project)
    absence = find_absence(NAME, project)
    if absence is not None:
        raise BrigadeError(f"{NAME} is absent: {absence}")
    pull_requests = read_pull_requests(inputs.project, _read_state(inputs.parameters), configuration, runtime)
    items = [{**pull_request, "task": _read_task(pull_request["head"])} for pull_request in pull_requests]
    summary = {counted: sum(item["state"] == counted for item in items) for counted in COUNTED_STATES}
    return {**describe_collection(NAME, runtime, summary, items), "cache": FRESH_AT_EACH_CALL}
