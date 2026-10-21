from operator import itemgetter
from pathlib import Path

from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.corpus.read_entity import Entity, read_entity
from brigade.corpus.run_awawa import run_awawa
from brigade.runtime import Runtime
from brigade.tasks.describe_command import describe_command
from brigade.tasks.match_glob import match_glob

TRIGGER_TYPE = "TRIGGER"
PATH_TRIGGERS = "KIND==path"
GLOB_FIELD = "GLOB"


def _matches_a_path(trigger: Entity, paths: list[str]) -> bool:
    globs = [field.value for field in trigger.fields if field.name == GLOB_FIELD]
    return any(match_glob(glob, path) for glob in globs for path in paths)


def list_trigger_rules(runtime: Runtime, instructions: Path, paths: list[str]) -> list[dict]:
    status = read_awawa_document(runtime.run_process, instructions, ("status", TRIGGER_TYPE, "--where", PATH_TRIGGERS))
    names = [entity["name"] for entity in sorted(status["entities"], key=itemgetter("file", "line"))]
    triggers = [read_entity(runtime.run_process, instructions, TRIGGER_TYPE, name) for name in names]
    return [
        {
            "trigger": trigger.name,
            **describe_command(
                run_awawa(
                    runtime.run_process,
                    instructions,
                    ("context", f"@TRIGGER.{trigger.name}", "--depth", "1", "--skip", "reasoning", str(instructions)),
                )
            ),
        }
        for trigger in triggers
        if _matches_a_path(trigger, paths)
    ]
