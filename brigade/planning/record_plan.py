from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.corpus.locate_entity_block import locate_entity_block
from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.corpus.read_awawa_file_document import read_awawa_file_document
from brigade.corpus.read_entity_template import read_entity_template
from brigade.errors import BrigadeError, CorpusLintFailed
from brigade.git.add_detached_worktree import add_detached_worktree
from brigade.git.check_ancestor import check_ancestor
from brigade.git.create_branch import create_branch
from brigade.git.fast_forward_branch import fast_forward_branch
from brigade.git.find_branch import find_branch
from brigade.git.list_worktrees import list_worktrees
from brigade.git.merge_fast_forward import merge_fast_forward
from brigade.git.remove_worktree import remove_worktree
from brigade.ledger.append_event import append_event
from brigade.ledger.plan_lint_failed import PlanLintFailed
from brigade.ledger.read_ledger import read_ledger
from brigade.planning.list_name_collisions import list_name_collisions
from brigade.planning.list_undeclared import list_undeclared
from brigade.planning.locate_entity_files import locate_entity_files
from brigade.planning.locate_request_file import locate_request_file
from brigade.planning.mark_request_planned import ENTITY_TYPE as REQUEST_TYPE
from brigade.planning.mark_request_planned import mark_request_planned
from brigade.planning.plan_publication import PlanPublication
from brigade.planning.publish_plan import publish_plan
from brigade.planning.read_entity_sites import read_entity_sites
from brigade.planning.read_plan import PlanEntity, read_plan
from brigade.planning.read_planning_request import PlanningRequest
from brigade.planning.review_plan_pull_request import review_plan_pull_request
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.system.ask_pull_request import PullRequestQuery, ask_pull_request
from brigade.system.read_configuration import CLI_KEY
from brigade.waves.locate_project_main import locate_project_main

MILESTONE_TYPE = "MILESTONE"
TASK_TYPE = "TASK"
GITHUB_FORGE = "github"
WORKTREES_DIRECTORY = "plans"
FILE_SUFFIX = "s.awawa"
PLAN_BRANCH_PREFIX = "plan/"
OPEN_PULL_REQUEST = "open"
ANCESTOR = 0


@dataclass(frozen=True)
class PlanRecording:
    request: PlanningRequest
    project: object
    plan_file: Path
    forge: object
    read_environment: Callable[[str], dict]


@dataclass(frozen=True)
class _PlanWrite:
    plan: tuple[PlanEntity, ...]
    branch: str
    run: str | None


def _read_run(runtime: Runtime) -> str | None:
    if runtime.paths.run_directory is None:
        return None
    return runtime.paths.run_directory.name


def _refuse_a_second_round(runtime: Runtime, request: str, run: str | None) -> None:
    if run is None:
        return
    spent = PlanLintFailed(request=request, run=run)
    if any(entry.event == spent for entry in read_ledger(runtime.paths.state_root).entries):
        raise BrigadeError(f"@{REQUEST_TYPE}.{request} spent its lint round in run {run}; the run ends blocked")


def _check_plan(plan: tuple[PlanEntity, ...]) -> PlanEntity:
    for plan_entity in plan:
        if plan_entity.type not in (MILESTONE_TYPE, TASK_TYPE):
            raise BrigadeError(
                f"the plan holds @{plan_entity.type}.{plan_entity.entity.name}, which is neither a MILESTONE nor a TASK"
            )
    milestones = [plan_entity for plan_entity in plan if plan_entity.type == MILESTONE_TYPE]
    if len(milestones) != 1:
        raise BrigadeError(f"the plan holds {len(milestones)} MILESTONE entities, not one")
    milestone = f"@{MILESTONE_TYPE}.{milestones[0].entity.name}"
    for plan_entity in plan:
        if plan_entity.type == TASK_TYPE and read_project_field(plan_entity.entity, MILESTONE_TYPE) != milestone:
            raise BrigadeError(
                f"the plan holds @{TASK_TYPE}.{plan_entity.entity.name}, whose MILESTONE is not {milestone}"
            )
    return milestones[0]


def _cut_blocks(plan_file: Path, plan: tuple[PlanEntity, ...]) -> list[str]:
    lines = plan_file.read_text(encoding="utf-8").splitlines(keepends=True)
    return [
        "".join(lines[index] for index in locate_entity_block(lines, plan_entity.type, plan_entity.entity.name)).strip(
            "\n"
        )
        + "\n"
        for plan_entity in plan
    ]


def _append_blocks(text: str, blocks: list[str]) -> str:
    return "\n".join([text.rstrip("\n") + "\n", *blocks] if text.strip() else blocks)


def _build_change(runtime: Runtime, recording: PlanRecording, worktree: Path, write: _PlanWrite) -> CorpusChange:
    plan = write.plan
    corpus = read_project_field(recording.project, "CORPUS")
    files = locate_entity_files(read_entity_sites(partial(read_awawa_document, runtime.run_process), worktree), corpus)
    destinations = [
        files.get(plan_entity.type, f"{corpus}/{plan_entity.type.lower()}{FILE_SUFFIX}") for plan_entity in plan
    ]
    file_names = tuple(dict.fromkeys(destinations))
    blocks = _cut_blocks(recording.plan_file, plan)

    def rewrite(texts: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            _append_blocks(
                text,
                [block for block, destination in zip(blocks, destinations, strict=True) if destination == file_name],
            )
            for file_name, text in zip(file_names, texts, strict=True)
        )

    root = Path(read_project_field(recording.project, "PATH"))
    return CorpusChange(
        repository=worktree,
        lock=locate_corpus_lock(runtime.paths.lock_directory, root),
        file_names=file_names,
        describe_message=lambda: f"brigade plan record: {write.branch}",
        rewrite=rewrite,
    )


def _write_on_branch(runtime: Runtime, recording: PlanRecording, worktree: Path, write: _PlanWrite) -> None:
    try:
        change_corpus_file(runtime.run_process, _build_change(runtime, recording, worktree, write))
        create_branch(runtime.run_process, worktree, write.branch)
    except CorpusLintFailed:
        append_event(runtime.paths, runtime.now, PlanLintFailed(request=recording.request.name, run=write.run))
        raise


def _check_against_corpus(runtime: Runtime, recording: PlanRecording, worktree: Path, plan) -> PlanEntity:
    collisions = list_name_collisions(
        read_entity_sites(partial(read_awawa_document, runtime.run_process), worktree), plan
    )
    if collisions:
        raise BrigadeError(", ".join(collisions))
    undeclared = list_undeclared(partial(read_entity_template, runtime.run_process), worktree, plan)
    if undeclared:
        raise BrigadeError(
            f"the schema of the corpus of @PROJECT.{recording.project.name} does not declare {', '.join(undeclared)}"
        )
    return _check_plan(plan)


def _write_plan(runtime: Runtime, recording: PlanRecording, write: _PlanWrite) -> PlanEntity:
    root = Path(read_project_field(recording.project, "PATH"))
    worktree = runtime.paths.cache_root / WORKTREES_DIRECTORY / recording.request.name
    main = locate_project_main(runtime.run_process, recording.project, recording.read_environment)
    add_detached_worktree(runtime.run_process, root, worktree, main)
    try:
        milestone = _check_against_corpus(runtime, recording, worktree, write.plan)
        _write_on_branch(runtime, recording, worktree, write)
    finally:
        remove_worktree(runtime.run_process, root, worktree)
    return milestone


def _merge_into_main(runtime: Runtime, recording: PlanRecording, branch: str) -> None:
    root = Path(read_project_field(recording.project, "PATH"))
    main = read_project_field(recording.project, "MAIN")
    holder = next(
        (worktree.path for worktree in list_worktrees(runtime.run_process, root) if worktree.branch == main), None
    )
    if holder is None:
        fast_forward_branch(runtime.run_process, root, main, branch)
    else:
        merge_fast_forward(runtime.run_process, holder, branch)


def _describe_publication(recording: PlanRecording, milestone: PlanEntity, branch: str) -> PlanPublication:
    return PlanPublication(
        repository=Path(read_project_field(recording.project, "PATH")),
        project=recording.project.name,
        base=read_project_field(recording.project, "MAIN"),
        branch=branch,
        title=f"docs(plan): {read_project_field(milestone.entity, 'TITLE')} (@{REQUEST_TYPE}.{recording.request.name})",
        body=recording.request.text,
        forge=recording.forge,
        forge_name=read_project_field(recording.project, "FORGE"),
        read_environment=recording.read_environment,
    )


def _deliver(runtime: Runtime, recording: PlanRecording, milestone: PlanEntity, branch: str) -> int | None:
    if read_project_field(recording.project, "FORGE") != GITHUB_FORGE:
        _merge_into_main(runtime, recording, branch)
        return None
    return publish_plan(runtime, _describe_publication(recording, milestone, branch))


def _holds_the_plan(runtime: Runtime, recording: PlanRecording, branch: str) -> bool:
    root = Path(read_project_field(recording.project, "PATH"))
    main = read_project_field(recording.project, "MAIN")
    return check_ancestor(runtime.run_process, root, branch, main).exit_code == ANCESTOR


def _complete_delivery(runtime: Runtime, recording: PlanRecording, milestone: PlanEntity, branch: str) -> int | None:
    forge_name = read_project_field(recording.project, "FORGE")
    if forge_name != GITHUB_FORGE:
        if not _holds_the_plan(runtime, recording, branch):
            _merge_into_main(runtime, recording, branch)
        return None
    query = PullRequestQuery(
        repository=read_project_field(recording.project, "PATH"),
        branch=branch,
        environment=recording.read_environment(CLI_KEY),
    )
    pull_request = ask_pull_request(recording.forge, forge_name, query, runtime)
    if pull_request is None:
        return _deliver(runtime, recording, milestone, branch)
    if pull_request.state == OPEN_PULL_REQUEST:
        review_plan_pull_request(runtime, _describe_publication(recording, milestone, branch), pull_request.number)
    return pull_request.number


def _mark_planned(runtime: Runtime, name: str, milestone: str, pr: int | None) -> None:
    root = runtime.paths.config_root

    def rewrite(texts: tuple[str, ...]) -> tuple[str, ...]:
        return (mark_request_planned(texts[0], name, milestone, pr),)

    change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=root,
            lock=locate_corpus_lock(runtime.paths.lock_directory, root),
            file_names=(locate_request_file(runtime, name),),
            describe_message=lambda: f"brigade plan record: @{REQUEST_TYPE}.{name} planned",
            rewrite=rewrite,
        ),
    )


def record_plan(runtime: Runtime, recording: PlanRecording) -> dict:
    name = recording.request.name
    run = _read_run(runtime)
    _refuse_a_second_round(runtime, name, run)
    root = Path(read_project_field(recording.project, "PATH"))
    plan = read_plan(partial(read_awawa_file_document, runtime.run_process), recording.plan_file)
    branch = f"{PLAN_BRANCH_PREFIX}{name}"
    if find_branch(runtime.run_process, root, branch):
        milestone = _check_plan(plan)
        pr = _complete_delivery(runtime, recording, milestone, branch)
    else:
        milestone = _write_plan(runtime, recording, _PlanWrite(plan=plan, branch=branch, run=run))
        pr = _deliver(runtime, recording, milestone, branch)
    _mark_planned(runtime, name, milestone.entity.name, pr)
    return {"request": name, "milestone": milestone.entity.name, "branch": branch, "pr": pr}
