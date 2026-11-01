from dataclasses import dataclass

from brigade.corpus.append_entity_block import append_entity_block
from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.corpus.quote_awawa_string import quote_awawa_string
from brigade.corpus.read_entity import Entity
from brigade.corpus.set_entity_status import set_entity_status
from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.format_instant import format_instant
from brigade.ledger.pattern_ratified import PatternRatified
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.studies.name_answer_file import name_answer_file
from brigade.triage.dismiss_cited_signals import EVIDENCE_FIELD, dismiss_cited_signals
from brigade.triage.read_new_pattern import PATTERN_TYPE, read_new_pattern
from brigade.waves.name_next_request import name_next_request
from brigade.waves.record_request import REQUESTS_FILE
from brigade.waves.render_request_block import NewRequest, render_request_block

RATIFIED_STATUS = "ratified"
WAVE_ACTION = "wave"
CONSTRAINT_ACTION = "constraint"
CONSTRAINT_KINDS = ("rule", "guard", "lint", "schema", "skill", "script")
ORDER_ACTION = "order"
DISMISS_ACTION = "dismiss"
CONSTRAINT_TYPE = "CONSTRAINT"
ORDER_TYPE = "ORDER"
PROPOSED_STATUS = "proposed"
ACTIVE_STATUS = "active"
EVIDENCE_SEPARATOR = "; "


@dataclass(frozen=True)
class Ratification:
    pattern: str
    kind: str | None


@dataclass(frozen=True)
class RatifiedPattern:
    project: str
    entities: dict


@dataclass(frozen=True)
class _Plan:
    pattern: Entity
    action: str
    project: str
    kind: str | None


def _check(runtime: Runtime, pattern: Entity, kind: str | None) -> _Plan:
    target = f"@{PATTERN_TYPE}.{pattern.name}"
    action = read_project_field(pattern, "ACTION")
    if action is None:
        raise BrigadeError(f"{target} names no ACTION")
    if action == DISMISS_ACTION:
        raise BrigadeError(f"{target} proposes its dismissal: brigade inbox dismiss {pattern.name}")
    project = read_project_field(pattern, "TARGET")
    if project is None:
        raise BrigadeError(f"{target} names no TARGET")
    if project not in {registered.name for registered in read_projects(runtime)}:
        raise BrigadeError(f"{target}: its TARGET {project} names no registered project")
    if action == ORDER_ACTION and read_project_field(pattern, "RECIPE") is None:
        raise BrigadeError(f"{target} places an order and names no RECIPE")
    if action == CONSTRAINT_ACTION and kind is None:
        raise BrigadeError(f"{target} becomes a constraint: --kind names its KIND")
    return _Plan(pattern=pattern, action=action, project=project, kind=kind)


def _describe_request(pattern: Entity, project: str) -> NewRequest:
    title = read_project_field(pattern, "TITLE")
    evidence = EVIDENCE_SEPARATOR.join(field.value for field in pattern.fields if field.name == EVIDENCE_FIELD)
    return NewRequest(project=project, text=f"{title}. Evidence: {evidence}", pattern=pattern.name)


def _render_constraint(pattern: Entity, kind: str) -> str:
    return (
        f"{CONSTRAINT_TYPE} {pattern.name}\n"
        f"\tTITLE {quote_awawa_string(read_project_field(pattern, 'TITLE'))}\n"
        f"\tKIND {kind}\n"
        f"\tFROM @{PATTERN_TYPE}.{pattern.name}\n"
        f"\tTARGET {quote_awawa_string(read_project_field(pattern, 'TARGET'))}\n"
        f"\tSTATUS {PROPOSED_STATUS}\n"
    )


def _render_order(pattern: Entity, project: str) -> str:
    return (
        f"{ORDER_TYPE} {pattern.name}\n"
        f"\tRECIPE {quote_awawa_string(read_project_field(pattern, 'RECIPE'))}\n"
        f"\tPROJECT @PROJECT.{project}\n"
        f"\tSTATUS {ACTIVE_STATUS}\n"
    )


def _list_files(action: str) -> tuple[str, ...]:
    entity_files = {
        WAVE_ACTION: (REQUESTS_FILE,),
        CONSTRAINT_ACTION: (name_answer_file(CONSTRAINT_TYPE), REQUESTS_FILE),
        ORDER_ACTION: (name_answer_file(ORDER_TYPE),),
    }
    return (name_answer_file(PATTERN_TYPE), *entity_files[action])


def _rewrite(runtime: Runtime, plan: _Plan, texts: tuple[str, ...], entities: dict) -> tuple[str, ...]:
    pattern = plan.pattern
    patterns = set_entity_status(texts[0], PATTERN_TYPE, pattern.name, RATIFIED_STATUS)
    if plan.action == ORDER_ACTION:
        entities["order"] = pattern.name
        return (patterns, append_entity_block(texts[1], _render_order(pattern, plan.project)))
    requests = texts[-1]
    request = name_next_request(requests, plan.project)
    block = render_request_block(request, _describe_request(pattern, plan.project), format_instant(runtime.now))
    entities["request"] = request
    if plan.action == WAVE_ACTION:
        return (patterns, append_entity_block(requests, block))
    entities["constraint"] = pattern.name
    return (
        patterns,
        append_entity_block(texts[1], _render_constraint(pattern, plan.kind)),
        append_entity_block(requests, block),
    )


def ratify_pattern(runtime: Runtime, ratification: Ratification) -> RatifiedPattern:
    root = runtime.paths.config_root
    plan = _check(runtime, read_new_pattern(runtime, ratification.pattern), ratification.kind)
    entities = {"pattern": ratification.pattern, "action": plan.action}

    def rewrite(texts: tuple[str, ...]) -> tuple[str, ...]:
        return _rewrite(runtime, plan, texts, entities)

    change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=root,
            lock=locate_corpus_lock(runtime.paths.lock_directory, root),
            file_names=_list_files(plan.action),
            describe_message=lambda: f"brigade inbox ratify: @{PATTERN_TYPE}.{ratification.pattern} {RATIFIED_STATUS}",
            rewrite=rewrite,
        ),
    )
    dismiss_cited_signals(runtime, plan.pattern)
    append_event(runtime.paths, runtime.now, PatternRatified(project=plan.project))
    return RatifiedPattern(project=plan.project, entities=entities)
