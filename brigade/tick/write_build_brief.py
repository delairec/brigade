from importlib.resources import files
from pathlib import Path
from string import Template

from brigade.system.create_directory import create_directory
from brigade.system.write_text_file import write_text_file
from brigade.tick.actions import LaunchTask
from brigade.tick.prepare_task_worktree import PreparedWorktree

BRIEF_TEMPLATE = files("brigade.tick") / "data" / "build-brief.md.tpl"
BRIEFS_DIRECTORY = "briefs"
ON_START = Template("cut from the head of $branch")
OFF_START = Template(
    "left as it stands, off the head of $branch: do not rebase it; the tick rebases it onto $branch"
    " once the checks of its pull request pass"
)


def write_build_brief(state_root: Path, action: LaunchTask, prepared: PreparedWorktree) -> Path:
    path = state_root / BRIEFS_DIRECTORY / f"{action.wave}-{action.task}.md"
    brief = Template(BRIEF_TEMPLATE.read_text(encoding="utf-8")).substitute(
        task=action.task,
        project=action.project,
        wave=action.wave,
        branch=action.branch,
        worktree=prepared.worktree.path,
        task_branch=prepared.worktree.branch,
        start=(ON_START if prepared.on_start else OFF_START).substitute(branch=action.branch),
    )
    create_directory(path.parent)
    write_text_file(path, brief)
    return path
