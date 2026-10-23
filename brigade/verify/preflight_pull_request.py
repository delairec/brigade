from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entities import Entity
from brigade.git.count_changed_lines import count_changed_lines
from brigade.git.fetch_branches import BranchesFetch, fetch_branches
from brigade.git.find_merge_base import find_merge_base
from brigade.git.list_added_lines import list_added_lines
from brigade.git.resolve_commit import resolve_commit
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.system.ask_pull_request_details import PullRequestDetailsQuery, ask_pull_request_details
from brigade.system.read_configuration import Configuration
from brigade.verify.check_ancestry import AncestryFacts, check_ancestry
from brigade.verify.check_body import check_body
from brigade.verify.check_check_runs import check_check_runs
from brigade.verify.check_corpus_at_head import check_corpus_at_head
from brigade.verify.check_privacy import PrivacyPatterns, check_privacy
from brigade.verify.check_promotion import PromotionFacts, check_promotion
from brigade.verify.check_untouched_files import UntouchedFilesFacts, check_untouched_files
from brigade.verify.measure_size import measure_size

DOCUMENT_SCHEMA_VERSION = 1
FORGE_NAME = "github"
REMOTE_BRANCH_PREFIX = "refs/remotes/origin/"


@dataclass(frozen=True)
class PreflightDemand:
    project: Entity
    task: str
    wave_branch: str
    pr: int
    forge: object
    environment: dict
    configuration: Configuration


@dataclass(frozen=True)
class TreeDemand:
    project: str
    ref: str
    worktree: None = None


@dataclass(frozen=True)
class _ComparedCommits:
    repository: Path
    wave_head: str
    base: str
    head: str


def _fetch_pull_request(runtime: Runtime, demand: PreflightDemand, repository: Path) -> dict:
    pull_request = ask_pull_request_details(
        demand.forge,
        FORGE_NAME,
        PullRequestDetailsQuery(repository=str(repository), number=demand.pr, environment=demand.environment),
        runtime,
    )
    fetch_branches(
        runtime.run_process,
        BranchesFetch(
            repository=repository, branches=(pull_request["head"], demand.wave_branch), environment=demand.environment
        ),
    )
    return pull_request


def _compare_commits(runtime: Runtime, repository: Path, wave_branch: str, head: str) -> _ComparedCommits:
    wave_head = resolve_commit(runtime.run_process, repository, f"{REMOTE_BRANCH_PREFIX}{wave_branch}")
    base = find_merge_base(runtime.run_process, repository, wave_head, head)
    return _ComparedCommits(repository=repository, wave_head=wave_head, base=base, head=head)


def _read_privacy_patterns(project: Entity) -> PrivacyPatterns:
    return PrivacyPatterns(
        private=tuple(field.value for field in project.fields if field.name == "PRIVATE"),
        public=tuple(field.value for field in project.fields if field.name == "PUBLIC"),
    )


def _run_checks(runtime: Runtime, demand: PreflightDemand, pull_request: dict, commits: _ComparedCommits) -> list:
    run_process = runtime.run_process
    project = demand.project.name
    head_tree = prepare_project_tree(TreeDemand(project=project, ref=commits.head), demand.configuration, runtime).root
    base_tree = prepare_project_tree(TreeDemand(project=project, ref=commits.base), demand.configuration, runtime).root
    changed = count_changed_lines(run_process, commits.repository, commits.base, commits.head)
    ancestry = AncestryFacts(
        repository=commits.repository, wave_branch=demand.wave_branch, wave_head=commits.wave_head, head=commits.head
    )
    return [
        check_ancestry(run_process, ancestry),
        check_check_runs(pull_request["checks"]),
        check_corpus_at_head(run_process, head_tree),
        check_promotion(run_process, PromotionFacts(head_tree=head_tree, task=demand.task, pr=demand.pr)),
        check_untouched_files(
            run_process, UntouchedFilesFacts(base_tree=base_tree, head_tree=head_tree, changed=changed)
        ),
        check_privacy(
            _read_privacy_patterns(demand.project),
            list_added_lines(run_process, commits.repository, commits.base, commits.head),
        ),
        check_body(pull_request["body"]),
        measure_size(changed),
    ]


def preflight_pull_request(runtime: Runtime, demand: PreflightDemand) -> dict:
    repository = Path(read_project_field(demand.project, "PATH"))
    pull_request = _fetch_pull_request(runtime, demand, repository)
    commits = _compare_commits(runtime, repository, demand.wave_branch, pull_request["head_sha"])
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": demand.project.name,
        "pr": demand.pr,
        "task": demand.task,
        "head": commits.head,
        "checks": _run_checks(runtime, demand, pull_request, commits),
    }
