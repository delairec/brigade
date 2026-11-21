import argparse
from pathlib import Path

from brigade.captures.refresh_review_captures import ReviewCaptureRefresh, refresh_review_captures
from brigade.command import Argument, Command
from brigade.commands._equip_preflight import equip_preflight
from brigade.commands._equip_registered_collector import equip_registered_collector
from brigade.commands._read_forge_environment import BUILD_SLOT, ForgeSlot, read_forge_environment
from brigade.errors import BrigadeError
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.git.read_current_branch import read_current_branch
from brigade.recipes.locate_recipes import locate_recipes
from brigade.registry.read_corpus_workspace import read_corpus_workspace
from brigade.registry.read_project_forge import NO_FORGE, read_project_forge
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runs.locate_source_worktree import locate_source_worktree
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.system.read_configuration import CONFIGURATION_REQUIRED, read_configuration
from brigade.tasks.find_task_base import find_task_base
from brigade.tasks.locate_task_worktree import locate_task_worktree
from brigade.verify.assemble_local_verify_context import assemble_local_verify_context
from brigade.verify.assemble_verify_context import assemble_verify_context
from brigade.verify.find_opened_task import find_opened_task
from brigade.verify.preflight_pull_request import PreflightDemand
from brigade.verify.preflight_task_branch import BranchPreflightDemand

DOCUMENT_SCHEMA_VERSION = 1
ABSENT = "none"
NAMED_BY_THE_BRANCH = None


def _render_commands(entries: list[dict]) -> str:
    return "".join(
        f"$ {entry['command']}\nexit {entry['exit_code']}\n{entry['stderr']}{entry['output']}" for entry in entries
    )


def _render_preflight(checks: list[dict]) -> str:
    return "".join(
        f"{check['result']}  {check['name']}\n" + "".join(f"  {finding}\n" for finding in check["findings"])
        for check in checks
    )


def _render_previous(previous: dict) -> str:
    findings = "".join(
        f"finding {finding['id']}: {finding['grade']} {finding['file']}:{finding['line']}, broken {finding['broken']}\n"
        f"  summary: {finding['summary'] or ABSENT}\n"
        f"  answer: {finding['answer'] or ABSENT}\n"
        for finding in previous["findings"]
    )
    return f"head {previous['head']}\nverdict {previous['verdict']}\n{findings}"


def _render_milestone(milestone: dict | None) -> str:
    if milestone is None:
        return "no milestone: the title of the task is its goal\n"
    return (
        f"milestone {milestone['name']}: {milestone['title']}\n"
        f"  subject: {milestone['subject'] or ABSENT}\n"
        + "".join(f"  desc: {desc}\n" for desc in milestone["desc"])
        + "".join(f"  source: {source}\n" for source in milestone["source"])
    )


def _render_goal(goal: dict | None, task: str) -> str:
    if goal is None:
        return f"the head defines no @TASK.{task}: the preflight promotion says so\n"
    return f"task {goal['task']}: {goal['title']}\n{_render_milestone(goal['milestone'])}"


def _render_captures(reference: dict) -> str:
    if reference["refusal"] is not None:
        return f"  refused: {reference['refusal']}\n"
    captures = reference["captures"]
    if captures is None:
        return "  captures: none at this head, brigade build capture wrote no PNG pair for this page\n"
    return f"  delivered: {captures['delivered']}\n  reference page: {captures['reference']}\n"


def _render_references(references: list[dict]) -> str:
    if not references:
        return f"{ABSENT}\n"
    return "".join(
        f"{reference['reference']}\n  covers: {reference['covers'] or ABSENT}\n{_render_captures(reference)}"
        for reference in references
    )


def _render_re_verification(document: dict) -> list[str]:
    if document["previous"] is None:
        return []
    return [
        f"# previous verdict\n{_render_previous(document['previous'])}",
        f"# repair diff\n{_render_commands([document['repair']])}",
    ]


def _render_text(document: dict) -> str:
    sections = [
        f"# head\n{document['head']}\n",
        f"# task\n{_render_commands(document['context'])}",
        f"# goal\n{_render_goal(document['goal'], document['task'])}",
        f"# reference\n{_render_references(document['references'])}",
        f"# diff\n{_render_commands([document['diff']])}",
        *_render_re_verification(document),
        f"# preflight\n{_render_preflight(document['preflight'])}",
        *([] if document["rules"] is None else [f"# rules\n{_render_commands(document['rules'])}"]),
        "# grades\n" + "".join(f"{grade}\n" for grade in document["grades"]),
    ]
    return "\n".join(sections).removesuffix("\n")


def _assemble_task_branch_context(runtime: Runtime, configuration: Configuration, worktree: Path) -> dict:
    located = locate_task_worktree(runtime, locate_source_worktree(runtime.paths, worktree), NAMED_BY_THE_BRANCH)
    branch_demand = BranchPreflightDemand(
        project=located.project,
        task=located.task,
        task_branch=read_current_branch(runtime.run_process, located.path),
        base_branch=located.base,
        configuration=configuration,
    )
    document = assemble_local_verify_context(runtime, branch_demand)
    refresh = ReviewCaptureRefresh(
        project=located.project.name,
        task=located.task,
        worktree=located.path,
        places=locate_recipes(located.path, located.project, runtime.paths),
        corpus=located.path / read_corpus_workspace(located.project),
        pr=None,
        forge=None,
        environment={},
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **refresh_review_captures(runtime, document, lambda: refresh)}


def review_context(request: argparse.Namespace, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime, CONFIGURATION_REQUIRED)
    run_process = runtime.run_process
    worktree = locate_worktree_root(run_process, Path.cwd())
    project = require_project_at(read_projects(runtime), locate_main_checkout(run_process, worktree))
    forge_name = read_project_forge(project)
    if forge_name == NO_FORGE:
        return _assemble_task_branch_context(runtime, configuration, worktree)
    if request.pr is None:
        raise BrigadeError(
            f"@PROJECT.{project.name} acts through the forge {forge_name}: the context names its pull request"
        )
    found = find_opened_task(runtime, project.name, request.pr)
    demand = PreflightDemand(
        project=project,
        task=found.opened.task,
        base_branch=find_task_base(runtime, worktree, project, found.opened.task),
        pr=request.pr,
        equipment=equip_registered_collector(project, configuration, runtime),
        plugins=equip_preflight(runtime),
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        **refresh_review_captures(
            runtime,
            assemble_verify_context(runtime, demand),
            lambda: ReviewCaptureRefresh(
                project=project.name,
                task=found.opened.task,
                worktree=worktree,
                places=locate_recipes(worktree, project, runtime.paths),
                corpus=worktree / read_corpus_workspace(project),
                pr=request.pr,
                forge=runtime.resolve_plugin("forge", forge_name),
                environment=read_forge_environment(configuration, ForgeSlot(forge_name, BUILD_SLOT), runtime),
            ),
        ),
    }


COMMAND = Command(
    path=("review", "context"),
    help="print in one read what the review of the pull request of a task judges",
    group_help="review the pull request of a task",
    arguments=(
        Argument(
            ("pr",),
            {"type": int, "nargs": "?", "help": "the number of the pull request, none on a project without a forge"},
        ),
    ),
    run=review_context,
    render_text=_render_text,
)
