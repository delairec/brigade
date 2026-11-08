from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.prepare_project_checkout import prepare_project_checkout
from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entities import Entity
from brigade.git.count_changed_lines import ChangedFile, count_changed_lines
from brigade.git.find_merge_base import find_merge_base
from brigade.git.list_added_lines import list_added_lines
from brigade.git.resolve_commit import resolve_commit
from brigade.registry.read_corpus_workspace import read_corpus_workspace
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.tasks.run_project_checks import ACCEPTANCE_FIELD
from brigade.verify.check_acceptance import AcceptanceFacts, check_acceptance
from brigade.verify.check_ancestry import AncestryFacts, check_ancestry
from brigade.verify.check_corpus_at_head import check_corpus_at_head
from brigade.verify.check_privacy import check_privacy
from brigade.verify.check_promotion import PromotionFacts, check_promotion
from brigade.verify.check_untouched_files import UntouchedFilesFacts, check_untouched_files
from brigade.verify.measure_size import measure_size
from brigade.verify.read_privacy_patterns import read_privacy_patterns

DOCUMENT_SCHEMA_VERSION = 1
NO_PULL_REQUEST = None


@dataclass(frozen=True)
class BranchPreflightDemand:
    project: Entity
    task: str
    task_branch: str
    base_branch: str
    configuration: Configuration


@dataclass(frozen=True)
class TreeDemand:
    project: str
    ref: str
    worktree: None = None


def _read_acceptance(project: Entity) -> tuple[str, ...]:
    return tuple(field.value for field in project.fields if field.name == ACCEPTANCE_FIELD)


@dataclass(frozen=True)
class _ComparedHead:
    head: str
    base: str
    changed: tuple[ChangedFile, ...]


def _run_corpus_checks(runtime: Runtime, demand: BranchPreflightDemand, compared: _ComparedHead) -> list[dict]:
    run_process = runtime.run_process
    project = demand.project.name
    head_tree = prepare_project_tree(TreeDemand(project=project, ref=compared.head), demand.configuration, runtime).root
    base_tree = prepare_project_tree(TreeDemand(project=project, ref=compared.base), demand.configuration, runtime).root
    return [
        check_corpus_at_head(run_process, head_tree),
        check_promotion(run_process, PromotionFacts(head_tree=head_tree, task=demand.task, pr=NO_PULL_REQUEST)),
        check_untouched_files(
            run_process,
            UntouchedFilesFacts(
                base_tree=base_tree,
                head_tree=head_tree,
                changed=compared.changed,
                folder=read_corpus_workspace(demand.project),
            ),
        ),
    ]


def preflight_task_branch(runtime: Runtime, demand: BranchPreflightDemand) -> dict:
    run_process = runtime.run_process
    project = demand.project.name
    repository = Path(read_project_field(demand.project, "PATH"))
    head = resolve_commit(run_process, repository, demand.task_branch)
    base_head = resolve_commit(run_process, repository, demand.base_branch)
    base = find_merge_base(run_process, repository, base_head, head)
    checkout = prepare_project_checkout(
        demand.project, TreeDemand(project=project, ref=head), demand.configuration, runtime
    ).root
    changed = count_changed_lines(run_process, repository, base, head)
    ancestry = AncestryFacts(repository=repository, base_branch=demand.base_branch, base_head=base_head, head=head)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": project,
        "task": demand.task,
        "head": head,
        "checks": [
            check_ancestry(run_process, ancestry),
            check_acceptance(
                run_process, AcceptanceFacts(head_tree=checkout, commands=_read_acceptance(demand.project))
            ),
            *_run_corpus_checks(runtime, demand, _ComparedHead(head=head, base=base, changed=changed)),
            check_privacy(read_privacy_patterns(demand.project), list_added_lines(run_process, repository, base, head)),
            measure_size(changed),
        ],
    }
