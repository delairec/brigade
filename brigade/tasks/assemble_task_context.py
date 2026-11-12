import argparse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.collect_anchors import collect_anchors
from brigade.corpus.decode_atom import decode_atom
from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.corpus.read_entity import Entity
from brigade.corpus.run_awawa import run_awawa
from brigade.errors import CommandFailed
from brigade.git.check_ancestor import check_ancestor
from brigade.planning.count_next_task_number import count_next_task_number
from brigade.runtime import Runtime
from brigade.system.create_directory import create_directory
from brigade.system.locate_setup_log import locate_setup_log
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import ProcessRecord
from brigade.tasks.describe_command import describe_command
from brigade.tasks.list_trigger_rules import list_trigger_rules
from brigade.tasks.locate_task_corpus import locate_task_corpus
from brigade.tasks.locate_task_worktree import TaskWorktree
from brigade.tasks.reserve_task_number import reserve_task_number
from brigade.waves.locate_forge_branch import locate_forge_branch

HEAD = "HEAD"
SPEC_FIELD = "SPEC"
ANCHOR_SEPARATOR = "::"
TRAILING_PUNCTUATION = ",."
AGENTS_FILE = "AGENTS.md"
TEMPORARY_DIRECTORY = "tmp"
WORKTREE_ROOT = "."
WHEN_DONE = ["brigade task check", "brigade task pr", "brigade task promote"]


@dataclass(frozen=True)
class TaskContextDemand:
    configuration: Configuration
    worktree: TaskWorktree
    attribution: list[str]
    read_environment: Callable[[str], dict]


def _describe_ancestry(runtime: Runtime, worktree: TaskWorktree) -> dict:
    record = check_ancestor(runtime.run_process, worktree.path, worktree.base, HEAD)
    return {"command": " ".join(record.argv), "exit_code": record.exit_code}


def _read_setup(runtime: Runtime, worktree: TaskWorktree) -> str | None:
    log = locate_setup_log(runtime.paths.setup_directory, worktree.project.name, worktree.task)
    if not log.exists():
        return None
    return log.read_text(encoding="utf-8")


def _list_task_paths(task: dict) -> list[str]:
    anchored = [anchor.partition(ANCHOR_SEPARATOR)[0] for anchor in collect_anchors(task["fields"])]
    named = [
        token.rstrip(TRAILING_PUNCTUATION)
        for field in task["fields"]
        if field["name"] == SPEC_FIELD
        for token in "".join(map(decode_atom, field["atoms"])).split()
    ]
    return [*anchored, *named]


def _list_rules(runtime: Runtime, configuration: Configuration, worktree: TaskWorktree) -> list[dict] | None:
    if configuration.instructions is None:
        return None
    task = read_awawa_document(runtime.run_process, locate_task_corpus(worktree), ("show", f"@TASK.{worktree.task}"))
    return list_trigger_rules(runtime, Path(configuration.instructions), _list_task_paths(task))


def _read_task(runtime: Runtime, worktree: TaskWorktree, target: str) -> ProcessRecord:
    record = run_awawa(
        runtime.run_process, locate_task_corpus(worktree), ("context", target, "--with-schema", WORKTREE_ROOT)
    )
    if record.exit_code != 0:
        raise CommandFailed(record.argv, record.exit_code, record.stderr)
    return record


def _read_agents(worktree: TaskWorktree) -> str | None:
    agents = worktree.path / AGENTS_FILE
    if not agents.exists():
        return None
    return agents.read_text(encoding="utf-8")


def _read_commands(project: Entity, field_name: str) -> list[str]:
    return [field.value for field in project.fields if field.name == field_name]


def _count_next_wave_number(runtime: Runtime, demand: TaskContextDemand) -> int:
    worktree = demand.worktree
    ref = locate_forge_branch(runtime.run_process, worktree.project, worktree.base, demand.read_environment)
    query = argparse.Namespace(project=worktree.project.name, ref=ref, worktree=None)
    tree = prepare_project_tree(query, demand.configuration, runtime)
    return count_next_task_number(read_awawa_document(runtime.run_process, tree.root, ("status",))["entities"])


def _reserve_temporary_directory(runtime: Runtime) -> str | None:
    if runtime.paths.run_directory is None:
        return None
    temporary_directory = runtime.paths.run_directory / TEMPORARY_DIRECTORY
    create_directory(temporary_directory)
    return str(temporary_directory)


def assemble_task_context(runtime: Runtime, demand: TaskContextDemand) -> dict:
    worktree = demand.worktree
    target = f"@TASK.{worktree.task}"
    return {
        "worktree": {"ancestry": _describe_ancestry(runtime, worktree), "setup": _read_setup(runtime, worktree)},
        "task": [
            describe_command(_read_task(runtime, worktree, target)),
            describe_command(
                run_awawa(
                    runtime.run_process, locate_task_corpus(worktree), ("lint", "--closure", target, WORKTREE_ROOT)
                )
            ),
        ],
        "rules": _list_rules(runtime, demand.configuration, worktree),
        "project": _read_agents(worktree),
        "acceptance": {
            "acceptance": _read_commands(worktree.project, "ACCEPTANCE"),
            "heavy": _read_commands(worktree.project, "HEAVY"),
        },
        "reserved": {
            "task_number": reserve_task_number(
                runtime.paths, worktree.project.name, _count_next_wave_number(runtime, demand)
            ),
            "temporary_directory": _reserve_temporary_directory(runtime),
            "attribution": demand.attribution,
        },
        "when_done": WHEN_DONE,
    }
