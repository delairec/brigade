from importlib.resources import files
from pathlib import Path
from string import Template

from brigade.git.add_branch_worktree import BranchWorktree
from brigade.system.create_directory import create_directory
from brigade.system.write_text_file import write_text_file
from brigade.tick.actions import LaunchTask

BRIEF_TEMPLATE = files("brigade.tick") / "data" / "build-brief.md.tpl"
BRIEFS_DIRECTORY = "briefs"


def write_build_brief(state_root: Path, action: LaunchTask, worktree: BranchWorktree) -> Path:
    path = state_root / BRIEFS_DIRECTORY / f"{action.request}-{action.task}.md"
    brief = Template(BRIEF_TEMPLATE.read_text(encoding="utf-8")).substitute(
        task=action.task,
        project=action.project,
        milestone=action.milestone,
        wave=action.wave,
        request=action.request,
        branch=action.branch,
        worktree=worktree.path,
        task_branch=worktree.branch,
    )
    create_directory(path.parent)
    write_text_file(path, brief)
    return path
