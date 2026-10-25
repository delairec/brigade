from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.run_awawa import run_awawa
from brigade.git.count_changed_lines import count_changed_lines
from brigade.git.find_merge_base import find_merge_base
from brigade.git.read_diff import read_diff
from brigade.git.resolve_commit import resolve_commit
from brigade.ledger.read_ledger import read_ledger
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.tasks.describe_command import describe_command
from brigade.tasks.list_trigger_rules import list_trigger_rules
from brigade.verify.preflight_pull_request import (
    REMOTE_BRANCH_PREFIX,
    PreflightDemand,
    TreeDemand,
    preflight_pull_request,
)
from brigade.verify.read_previous_verdict import VerifiedPullRequest, read_previous_verdict
from brigade.verify.read_repair_diff import RepairSpan, read_repair_diff

GRADES = ("critical", "high", "medium", "low")
TREE_ROOT = "."


@dataclass(frozen=True)
class Judged:
    head: str
    base: str
    wave_head: str
    repository: Path


def _locate_judged(runtime: Runtime, demand: PreflightDemand, head: str) -> Judged:
    repository = Path(read_project_field(demand.project, "PATH"))
    wave_head = resolve_commit(runtime.run_process, repository, f"{REMOTE_BRANCH_PREFIX}{demand.wave_branch}")
    return Judged(
        head=head,
        base=find_merge_base(runtime.run_process, repository, wave_head, head),
        wave_head=wave_head,
        repository=repository,
    )


def _read_task(runtime: Runtime, demand: PreflightDemand, head: str) -> list[dict]:
    tree = prepare_project_tree(TreeDemand(project=demand.project.name, ref=head), demand.configuration, runtime).root
    target = f"@TASK.{demand.task}"
    return [
        describe_command(run_awawa(runtime.run_process, tree, ("context", target, "--with-schema", TREE_ROOT))),
        describe_command(run_awawa(runtime.run_process, tree, ("lint", "--closure", target, TREE_ROOT))),
    ]


def _list_rules(runtime: Runtime, demand: PreflightDemand, judged: Judged) -> list[dict] | None:
    instructions = demand.configuration.instructions
    if instructions is None:
        return None
    changed = count_changed_lines(runtime.run_process, judged.repository, judged.base, judged.head)
    return list_trigger_rules(runtime, Path(instructions), [changed_file.path for changed_file in changed])


def _read_repair(runtime: Runtime, judged: Judged, previous: dict | None) -> dict | None:
    if previous is None:
        return None
    span = RepairSpan(
        repository=judged.repository,
        wave_head=judged.wave_head,
        judged_head=previous["head"],
        head=judged.head,
        base=judged.base,
    )
    return describe_command(read_repair_diff(runtime.run_process, span))


def assemble_verify_context(runtime: Runtime, demand: PreflightDemand) -> dict:
    preflight = preflight_pull_request(runtime, demand)
    judged = _locate_judged(runtime, demand, preflight["head"])
    previous = read_previous_verdict(
        [entry.event for entry in read_ledger(runtime.paths.state_root).entries],
        VerifiedPullRequest(project=demand.project.name, task=demand.task, pr=demand.pr),
    )
    return {
        "project": demand.project.name,
        "pr": demand.pr,
        "task": demand.task,
        "head": judged.head,
        "context": _read_task(runtime, demand, judged.head),
        "diff": describe_command(read_diff(runtime.run_process, judged.repository, judged.base, judged.head)),
        "previous": previous,
        "repair": _read_repair(runtime, judged, previous),
        "preflight": preflight["checks"],
        "rules": _list_rules(runtime, demand, judged),
        "grades": list(GRADES),
    }
