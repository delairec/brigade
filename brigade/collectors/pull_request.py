import dataclasses
from dataclasses import dataclass
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.corpus.prepare_project_checkout import prepare_project_checkout
from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entities import Entity
from brigade.git.count_changed_lines import count_changed_lines
from brigade.git.fetch_branches import BranchesFetch, fetch_branches
from brigade.git.find_merge_base import find_merge_base
from brigade.git.list_added_lines import list_added_lines
from brigade.git.resolve_commit import resolve_commit
from brigade.registry.read_corpus_workspace import read_corpus_workspace
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_project_forge import NO_FORGE
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.system.ask_pull_request_details import PullRequestDetailsQuery, ask_pull_request_details
from brigade.system.parse_configuration import CLI_KEY
from brigade.system.read_account_environment import UNBOUND_ENVIRONMENT, ForgeAccount, read_account_environment
from brigade.tasks.run_project_checks import ACCEPTANCE_FIELD
from brigade.verify.read_privacy_patterns import read_privacy_patterns

NAME = "pull-request"
REMOTE_BRANCH_PREFIX = "refs/remotes/origin/"
FRESH_AT_EACH_CALL = False
NO_ITEMS = []


@dataclass(frozen=True)
class TreeDemand:
    project: str
    ref: str
    worktree: None = None


@dataclass(frozen=True)
class _PullRequestQuery:
    repository: Path
    pr: int
    base_branch: str
    equipment: CollectorEquipment


def _read_environment(equipment: CollectorEquipment, runtime: Runtime) -> dict:
    if equipment.forge_name == NO_FORGE:
        return UNBOUND_ENVIRONMENT
    account = ForgeAccount(forge=equipment.forge, forge_name=equipment.forge_name, key=CLI_KEY)
    return read_account_environment(account, equipment.configuration, runtime)


def _fetch_pull_request(query: _PullRequestQuery, runtime: Runtime) -> dict:
    equipment = query.equipment
    environment = _read_environment(equipment, runtime)
    pull_request = ask_pull_request_details(
        equipment.forge,
        equipment.forge_name,
        PullRequestDetailsQuery(repository=str(query.repository), number=query.pr, environment=environment),
        runtime,
    )
    fetch_branches(
        runtime.run_process,
        BranchesFetch(
            repository=query.repository,
            branches=(pull_request["head"], query.base_branch),
            environment=environment,
        ),
    )
    return pull_request


def _describe_revisions(project: Entity, query: _PullRequestQuery, head: str, runtime: Runtime) -> dict:
    run_process = runtime.run_process
    repository = query.repository
    base_head = resolve_commit(run_process, repository, f"{REMOTE_BRANCH_PREFIX}{query.base_branch}")
    base = find_merge_base(run_process, repository, base_head, head)
    configuration = query.equipment.configuration
    return {
        "base_head": base_head,
        "base": base,
        "head": head,
        "head_tree": str(prepare_project_tree(TreeDemand(project.name, head), configuration, runtime).root),
        "base_tree": str(prepare_project_tree(TreeDemand(project.name, base), configuration, runtime).root),
        "checkout": str(prepare_project_checkout(project, TreeDemand(project.name, head), configuration, runtime).root),
        "folder": str(read_corpus_workspace(project)),
        "changed": [
            dataclasses.asdict(changed) for changed in count_changed_lines(run_process, repository, base, head)
        ],
        "added_lines": [dataclasses.asdict(added) for added in list_added_lines(run_process, repository, base, head)],
    }


def _describe_project_rules(project: Entity) -> dict:
    privacy = read_privacy_patterns(project)
    return {
        "acceptance": [field.value for field in project.fields if field.name == ACCEPTANCE_FIELD],
        "privacy": {"private": list(privacy.private), "public": list(privacy.public)},
    }


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    project = require_project_at(read_projects(runtime), inputs.project)
    repository = Path(read_project_field(project, "PATH"))
    query = _PullRequestQuery(
        repository=repository,
        pr=int(inputs.parameters["pr"]),
        base_branch=inputs.parameters["base"],
        equipment=equipment,
    )
    pull_request = _fetch_pull_request(query, runtime)
    summary = {
        "project": project.name,
        "pr": query.pr,
        "task": inputs.parameters["task"],
        "base_branch": query.base_branch,
        "repository": str(repository),
        **_describe_revisions(project, query, pull_request["head_sha"], runtime),
        "check_runs": pull_request["checks"],
        "body": pull_request["body"],
        **_describe_project_rules(project),
    }
    return {**describe_collection(NAME, runtime, summary, NO_ITEMS), "cache": FRESH_AT_EACH_CALL}
