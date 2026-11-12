from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.run_awawa import run_awawa
from brigade.git.count_changed_lines import count_changed_lines
from brigade.git.read_diff import read_diff
from brigade.ledger.read_ledger import read_ledger
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.tasks.describe_command import describe_command
from brigade.tasks.list_trigger_rules import list_trigger_rules
from brigade.verify.read_previous_verdict import VerifiedPullRequest, read_previous_verdict
from brigade.verify.read_repair_diff import RepairSpan, read_repair_diff

GRADES = ("critical", "high", "medium", "low")
TREE_ROOT = "."


@dataclass(frozen=True)
class JudgedTask:
    project: str
    task: str
    pr: int | None
    head: str
    base: str
    base_head: str
    repository: Path
    preflight: list[dict]
    configuration: Configuration


@dataclass(frozen=True)
class TreeDemand:
    project: str
    ref: str
    worktree: None = None


def _read_task(runtime: Runtime, judged: JudgedTask) -> list[dict]:
    tree = prepare_project_tree(TreeDemand(project=judged.project, ref=judged.head), judged.configuration, runtime).root
    target = f"@TASK.{judged.task}"
    return [
        describe_command(run_awawa(runtime.run_process, tree, ("context", target, "--with-schema", TREE_ROOT))),
        describe_command(run_awawa(runtime.run_process, tree, ("lint", "--closure", target, TREE_ROOT))),
    ]


def _list_rules(runtime: Runtime, judged: JudgedTask) -> list[dict] | None:
    instructions = judged.configuration.instructions
    if instructions is None:
        return None
    changed = count_changed_lines(runtime.run_process, judged.repository, judged.base, judged.head)
    return list_trigger_rules(runtime, Path(instructions), [changed_file.path for changed_file in changed])


def _read_repair(runtime: Runtime, judged: JudgedTask, previous: dict | None) -> dict | None:
    if previous is None:
        return None
    span = RepairSpan(
        repository=judged.repository,
        base_head=judged.base_head,
        judged_head=previous["head"],
        head=judged.head,
        base=judged.base,
    )
    return describe_command(read_repair_diff(runtime.run_process, span))


def describe_judged_task(runtime: Runtime, judged: JudgedTask) -> dict:
    previous = read_previous_verdict(
        [entry.event for entry in read_ledger(runtime.paths.state_root).entries],
        VerifiedPullRequest(project=judged.project, task=judged.task, pr=judged.pr),
    )
    return {
        "project": judged.project,
        "pr": judged.pr,
        "task": judged.task,
        "head": judged.head,
        "context": _read_task(runtime, judged),
        "diff": describe_command(read_diff(runtime.run_process, judged.repository, judged.base, judged.head)),
        "previous": previous,
        "repair": _read_repair(runtime, judged, previous),
        "preflight": judged.preflight,
        "rules": _list_rules(runtime, judged),
        "grades": list(GRADES),
    }
