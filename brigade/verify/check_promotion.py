from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.collect_anchors import collect_anchors
from brigade.corpus.decode_atom import decode_atom
from brigade.corpus.read_entity_document import read_entity_document
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.verify.judge_findings import judge_findings
from brigade.verify.list_task_references import list_task_references

NAME = "promotion"
IMPLEMENTED = "implemented"
ANCHOR_SEPARATOR = "::"
NO_PULL_REQUEST = "no pull request"
UNRATIFIED = (None, None)


@dataclass(frozen=True)
class PromotionFacts:
    base_tree: Path
    head_tree: Path
    repository_tree: Path
    task: str
    pr: int | None
    changed: tuple[str, ...]


def _read_atom(field: dict) -> str:
    atom = field["atoms"][0]
    return decode_atom(atom)


def _read_value(fields: list, name: str) -> str | None:
    return next((_read_atom(field) for field in fields if field["name"] == name), None)


def _resolves(repository_tree: Path, anchor: str) -> bool:
    path, _separator, text = anchor.partition(ANCHOR_SEPARATOR)
    file = (repository_tree / path).resolve()
    return (
        file.is_relative_to(repository_tree.resolve())
        and file.is_file()
        and text in file.read_text(encoding="utf-8", errors="replace")
    )


def _list_changed_references(facts: PromotionFacts, target: str, judged: list[dict], based: list[dict]) -> list[str]:
    revised = {reference["reference"] for reference in based if reference["revises"] is not None}
    return [
        f"{reference['reference']} is the REFERENCE {target} is judged against, and its branch changes it:"
        " a task delivering its reference says so with REVISES at the base of its branch"
        for reference in judged
        if reference["reference"] in facts.changed and reference["reference"] not in revised
    ]


def _identify(reference: dict) -> tuple[str, str | None]:
    return reference["reference"], reference["covers"]


def _name_entry(reference: dict) -> str:
    return f"{reference['reference']}, COVERS {reference['covers']}"


def _list_removed_references(target: str, based: list[dict], shown: list[dict]) -> list[str]:
    kept = {_identify(reference) for reference in shown}
    return [
        f"{_name_entry(reference)}, is a REFERENCE of {target} at the base of its branch, and its branch removes it:"
        " the review judges the task against its REFERENCE at the base"
        for reference in based
        if _identify(reference) not in kept
    ]


def _list_waivers(target: str, based: list[dict], shown: list[dict]) -> list[str]:
    ratified = {_identify(reference): (reference["revises"], reference["reads"]) for reference in based}
    return [
        f"the branch of {target} adds or changes the REVISES or the READ under its REFERENCE {_name_entry(reference)}:"
        " the builder never does, the planner writes them at ratification"
        for reference in shown
        if (reference["revises"], reference["reads"]) != ratified.get(_identify(reference), UNRATIFIED)
    ]


def _list_unreadable_reads(facts: PromotionFacts, target: str, judged: list[dict]) -> list[str]:
    return [
        f"the READ {reference['reads']} under the REFERENCE {reference['reference']} of {target}"
        " names no file of the repository: the review cannot read it"
        for reference in judged
        if reference["reads"] is not None and not _resolves(facts.repository_tree, reference["reads"])
    ]


def _list_unreadable_references(facts: PromotionFacts, target: str, judged: list[dict]) -> list[str]:
    return [
        f"the REFERENCE {_name_entry(reference)}, of {target} names no file of the repository:"
        " the review cannot open it, and its branch cannot repoint it: a plan pull request fixes it at the base"
        for reference in judged
        if not _resolves(facts.repository_tree, reference["reference"])
    ]


def _judge_references(
    run_process: Callable[[ProcessRequest], ProcessRecord], facts: PromotionFacts, shown: dict
) -> list:
    target = f"@TASK.{facts.task}"
    at_head = list_task_references(shown)
    based = read_entity_document(run_process, facts.base_tree, target)
    at_base = [] if based is None else list_task_references(based)
    judged = at_head if based is None else at_base
    return [
        *_list_changed_references(facts, target, judged, at_base),
        *_list_removed_references(target, at_base, at_head),
        *_list_waivers(target, at_base, at_head),
        *_list_unreadable_reads(facts, target, judged),
        *_list_unreadable_references(facts, target, judged),
    ]


def check_promotion(run_process: Callable[[ProcessRequest], ProcessRecord], facts: PromotionFacts) -> dict:
    target = f"@TASK.{facts.task}"
    shown = read_entity_document(run_process, facts.head_tree, target)
    if shown is None:
        return judge_findings(NAME, [f"{target} is not defined at the head"])
    fields = shown["fields"]
    findings = []
    status = _read_value(fields, "STATUS")
    if status != IMPLEMENTED:
        findings.append(f"{target} is STATUS {status}, not implemented")
    delivered_by = _read_value(fields, "DELIVERED_BY")
    if facts.pr is not None and delivered_by != str(facts.pr):
        findings.append(
            f"{target} is delivered by {f'#{delivered_by}' if delivered_by else NO_PULL_REQUEST}, not by #{facts.pr}"
        )
    specs = [field for field in fields if field["name"] == "SPEC"]
    for rank, spec in enumerate(specs, start=1):
        if not any(_resolves(facts.repository_tree, anchor) for anchor in collect_anchors(spec["fields"])):
            findings.append(f"SPEC {rank} has no IMPL whose anchor resolves: {_read_atom(spec)}")
    findings.extend(_judge_references(run_process, facts, shown))
    return judge_findings(NAME, findings)
