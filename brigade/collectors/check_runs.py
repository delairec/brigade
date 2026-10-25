from collections import Counter
from dataclasses import dataclass

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.find_absence import find_absence
from brigade.collecting.name_check_run_subject import name_check_run_subject
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.errors import BrigadeError
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.system.ask_check_runs import CheckRunsQuery, ask_check_runs
from brigade.system.ask_job_steps import JobStepsQuery, ask_job_steps
from brigade.system.parse_configuration import CLI_KEY
from brigade.system.read_account_environment import ForgeAccount, read_account_environment

NAME = "check-runs"
MAIN_FIELD = "MAIN"
FAILING_CONCLUSIONS = ("failure", "timed_out", "startup_failure")
FAILED_STEP = "failure"
FRESH_AT_EACH_CALL = False


def _find_first_failing_step(steps: list[dict] | None) -> str | None:
    if steps is None:
        return None
    return next((step["name"] for step in steps if step["conclusion"] == FAILED_STEP), None)


@dataclass(frozen=True)
class _ForgeReading:
    repository: str
    environment: dict
    equipment: CollectorEquipment


def _describe_failing_check_run(check_run: dict, reading: _ForgeReading, runtime: Runtime) -> dict:
    steps = ask_job_steps(
        reading.equipment.forge,
        reading.equipment.forge_name,
        JobStepsQuery(repository=reading.repository, link=check_run["link"], environment=reading.environment),
        runtime,
    )
    return {**check_run, "first_failing_step": _find_first_failing_step(steps)}


def _list_failing_check_runs(reading: _ForgeReading, branch: str, runtime: Runtime) -> list[dict]:
    check_runs = ask_check_runs(
        reading.equipment.forge,
        reading.equipment.forge_name,
        CheckRunsQuery(repository=reading.repository, branch=branch, environment=reading.environment),
        runtime,
    )
    return [
        _describe_failing_check_run(check_run, reading, runtime)
        for check_run in check_runs
        if check_run["conclusion"] in FAILING_CONCLUSIONS
    ]


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    project = require_project_at(read_projects(runtime), inputs.project)
    absence = find_absence(NAME, project)
    if absence is not None:
        raise BrigadeError(f"{NAME} is absent: {absence}")
    account = ForgeAccount(forge=equipment.forge, forge_name=equipment.forge_name, key=CLI_KEY)
    reading = _ForgeReading(
        repository=str(inputs.project),
        environment=read_account_environment(account, equipment.configuration, runtime),
        equipment=equipment,
    )
    items = _list_failing_check_runs(reading, read_project_field(project, MAIN_FIELD), runtime)
    summary = dict(Counter(name_check_run_subject(item) for item in items))
    return {**describe_collection(NAME, runtime, summary, items), "cache": FRESH_AT_EACH_CALL}
