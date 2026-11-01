from importlib.resources import files
from pathlib import Path
from string import Template

from brigade.corpus.read_entity import Entity
from brigade.system.create_directory import create_directory
from brigade.system.write_text_file import write_text_file
from brigade.tick.actions import RebuildTask
from brigade.tick.name_task_branch import name_task_branch

BRIEF_TEMPLATE = files("brigade.tick") / "data" / "rebuild-brief.md.tpl"
BRIEFS_DIRECTORY = "briefs"
TASK_TYPE = "TASK"


def _render_entity(entity: Entity) -> str:
    return "\n".join([f"{TASK_TYPE} {entity.name}", *(f"\t{field.name} {field.value}" for field in entity.fields)])


def write_rebuild_brief(state_root: Path, action: RebuildTask) -> Path:
    path = state_root / BRIEFS_DIRECTORY / f"{action.wave}-{action.task}-rebuild.md"
    brief = Template(BRIEF_TEMPLATE.read_text(encoding="utf-8")).substitute(
        task=action.task,
        project=action.project,
        wave=action.wave,
        base=action.base,
        pr=action.pr,
        worktree=action.worktree,
        task_branch=name_task_branch(action.base, action.task),
        on_pull_request=_render_entity(action.amendment.on_pull_request),
        on_wave=_render_entity(action.amendment.on_wave),
    )
    create_directory(path.parent)
    write_text_file(path, brief)
    return path
