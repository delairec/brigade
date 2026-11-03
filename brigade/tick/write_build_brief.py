from importlib.resources import files
from pathlib import Path
from string import Template

from brigade.corpus.read_entity import Entity
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
RULED_TASK = Template(
    "\n@TASK.$task reads differently on $start than in the corpus of the worktree;"
    " that reading is more recent and prevails:\n\n```\nTASK $task\n$fields```\n"
)
NO_RULING = ""


def _describe_ruling(prepared: PreparedWorktree, ruled_task: Entity | None) -> str:
    if ruled_task is None:
        return NO_RULING
    return RULED_TASK.substitute(
        task=ruled_task.name,
        start=prepared.worktree.start,
        fields="".join(f"\t{field.name} {field.value}\n" for field in ruled_task.fields),
    )


def write_build_brief(
    state_root: Path, action: LaunchTask, prepared: PreparedWorktree, ruled_task: Entity | None
) -> Path:
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
    write_text_file(path, brief + _describe_ruling(prepared, ruled_task))
    return path
