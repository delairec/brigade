from importlib.resources import files
from pathlib import Path
from string import Template

from brigade.system.create_directory import create_directory
from brigade.system.write_text_file import write_text_file
from brigade.tick.actions import LaunchCheckRepair
from brigade.tick.name_task_branch import name_task_branch

BRIEF_TEMPLATE = files("brigade.tick") / "data" / "repair-brief.md.tpl"
BRIEFS_DIRECTORY = "briefs"
NO_LOG_KEPT = "The forge keeps no log of this check."


def _describe_tail(tail: str | None) -> str:
    if tail is None:
        return NO_LOG_KEPT
    return f"```\n{tail}\n```"


def write_repair_brief(state_root: Path, action: LaunchCheckRepair, logs: list[dict]) -> Path:
    path = state_root / BRIEFS_DIRECTORY / f"{action.wave}-{action.task}-checks.md"
    brief = Template(BRIEF_TEMPLATE.read_text(encoding="utf-8")).substitute(
        pr=action.pr,
        task=action.task,
        project=action.project,
        wave=action.wave,
        branch=action.branch,
        worktree=action.worktree,
        task_branch=name_task_branch(action.branch, action.task),
        logs="".join(f"\n## {log['name']}\n\n{_describe_tail(log['tail'])}\n" for log in logs),
    )
    create_directory(path.parent)
    write_text_file(path, brief)
    return path
