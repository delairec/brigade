from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.find_absence import find_absence
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.errors import BrigadeError
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.system.ask_pull_requests import PullRequestsQuery, ask_pull_requests
from brigade.system.ask_review_threads import ReviewThreadsQuery, ask_review_threads
from brigade.system.parse_configuration import CLI_KEY
from brigade.system.read_account_environment import ForgeAccount, read_account_environment

NAME = "pr-threads"
OPEN_STATE = "open"
FRESH_AT_EACH_CALL = False


def _describe_thread(pull_request: int, thread: dict) -> dict:
    return {
        "thread": thread["id"],
        "pull_request": pull_request,
        "path": thread["file"],
        "line": thread["line"],
        "author": thread["author"],
        "comment": thread["body"],
    }


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    project = require_project_at(read_projects(runtime), inputs.project)
    absence = find_absence(NAME, project)
    if absence is not None:
        raise BrigadeError(f"{NAME} is absent: {absence}")
    account = ForgeAccount(forge=equipment.forge, forge_name=equipment.forge_name, key=CLI_KEY)
    account_environment = read_account_environment(account, equipment.configuration, runtime)
    repository = str(inputs.project)
    pull_requests = ask_pull_requests(
        equipment.forge,
        equipment.forge_name,
        PullRequestsQuery(repository=repository, state=OPEN_STATE, environment=account_environment),
        runtime,
    )
    threads = {
        pull_request["number"]: ask_review_threads(
            equipment.forge,
            equipment.forge_name,
            ReviewThreadsQuery(repository=repository, number=pull_request["number"], environment=account_environment),
            runtime,
        )
        for pull_request in pull_requests
    }
    items = [_describe_thread(number, thread) for number, listed in threads.items() for thread in listed]
    summary = {str(number): len(listed) for number, listed in threads.items()}
    return {**describe_collection(NAME, runtime, summary, items), "cache": FRESH_AT_EACH_CALL}
