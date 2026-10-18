from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entity import read_entity
from brigade.errors import BrigadeError
from brigade.git.count_changed_lines import count_changed_lines
from brigade.git.fetch_branches import BranchesFetch, fetch_branches
from brigade.git.find_merge_base import find_merge_base
from brigade.git.list_added_lines import list_added_lines
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.git.resolve_commit import resolve_commit
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.system.ask_pull_request_details import PullRequestDetailsQuery, ask_pull_request_details
from brigade.system.read_configuration import Configuration
from brigade.verify.check_ancestry import AncestryFacts, check_ancestry
from brigade.verify.check_body import check_body
from brigade.verify.check_check_runs import check_check_runs
from brigade.verify.check_corpus_at_head import check_corpus_at_head
from brigade.verify.check_privacy import check_privacy
from brigade.verify.check_promotion import PromotionFacts, check_promotion
from brigade.verify.check_untouched_files import UntouchedFilesFacts, check_untouched_files
from brigade.verify.measure_size import measure_size

DOCUMENT_SCHEMA_VERSION = 1
FORGE_NAME = "github"
REMOTE_BRANCH_PREFIX = "refs/remotes/origin/"


@dataclass(frozen=True)
class PreflightDemand:
    path: Path
    pr: int
    forge: object
    environment: dict
    configuration: Configuration


@dataclass(frozen=True)
class TreeDemand:
    project: str
    ref: str
    worktree: None = None


def _find_opened_task(runtime: Runtime, project: str, pr: int) -> tuple[TaskPrOpened, str]:
    events = [entry.event for entry in read_ledger(runtime.paths.state_root).entries]
    opened = [
        event for event in events if isinstance(event, TaskPrOpened) and (event.project, event.pr) == (project, pr)
    ]
    if not opened:
        raise BrigadeError(f"no task.pr_opened of @PROJECT.{project} names the pull request #{pr}")
    wave_branch = next(
        event.branch for event in events if isinstance(event, WaveStarted) and event.wave == opened[-1].wave
    )
    return opened[-1], wave_branch


def preflight_pull_request(runtime: Runtime, demand: PreflightDemand) -> dict:
    run_process = runtime.run_process
    project = require_project_at(
        read_projects(runtime), locate_main_checkout(run_process, locate_worktree_root(run_process, demand.path))
    )
    repository = Path(read_project_field(project, "PATH"))
    opened, wave_branch = _find_opened_task(runtime, project.name, demand.pr)
    pull_request = ask_pull_request_details(
        demand.forge,
        FORGE_NAME,
        PullRequestDetailsQuery(repository=str(repository), number=demand.pr, environment=demand.environment),
        runtime,
    )
    fetch_branches(
        run_process,
        BranchesFetch(
            repository=repository, branches=(pull_request["head"], wave_branch), environment=demand.environment
        ),
    )
    head = pull_request["head_sha"]
    wave_head = resolve_commit(run_process, repository, f"{REMOTE_BRANCH_PREFIX}{wave_branch}")
    base = find_merge_base(run_process, repository, wave_head, head)
    head_tree = prepare_project_tree(TreeDemand(project=project.name, ref=head), demand.configuration, runtime).root
    base_tree = prepare_project_tree(TreeDemand(project=project.name, ref=base), demand.configuration, runtime).root
    changed = count_changed_lines(run_process, repository, base, head)
    title = read_project_field(read_entity(run_process, head_tree, "TASK", opened.task), "TITLE")
    private_patterns = tuple(field.value for field in project.fields if field.name == "PRIVATE")
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": project.name,
        "pr": demand.pr,
        "task": opened.task,
        "head": head,
        "checks": [
            check_ancestry(
                run_process,
                AncestryFacts(repository=repository, wave_branch=wave_branch, wave_head=wave_head, head=head),
            ),
            check_check_runs(pull_request["checks"]),
            check_corpus_at_head(run_process, head_tree),
            check_promotion(run_process, PromotionFacts(head_tree=head_tree, task=opened.task, pr=demand.pr)),
            check_untouched_files(
                run_process, UntouchedFilesFacts(base_tree=base_tree, head_tree=head_tree, changed=changed)
            ),
            check_privacy(private_patterns, list_added_lines(run_process, repository, base, head)),
            check_body(pull_request["body"], title),
            measure_size(changed),
        ],
    }
