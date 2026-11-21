from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.collect_anchors import collect_anchors
from brigade.corpus.decode_atom import decode_atom
from brigade.corpus.read_entity_document import read_entity_document
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.verify.judge_findings import judge_findings

NAME = "promotion"
IMPLEMENTED = "implemented"
ANCHOR_SEPARATOR = "::"
NO_PULL_REQUEST = "no pull request"
REFERENCE_FIELD = "REFERENCE"
REVISES_FIELD = "REVISES"


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


def _is_revised(reference: dict) -> bool:
    return any(field["name"] == REVISES_FIELD for field in reference["fields"])


def _list_revised_references(run_process: Callable[[ProcessRequest], ProcessRecord], facts: PromotionFacts) -> set:
    based = read_entity_document(run_process, facts.base_tree, f"@TASK.{facts.task}")
    if based is None:
        return set()
    return {_read_atom(field) for field in based["fields"] if field["name"] == REFERENCE_FIELD and _is_revised(field)}


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
    changed = [_read_atom(field) for field in fields if field["name"] == REFERENCE_FIELD]
    changed = [path for path in changed if path in facts.changed]
    if changed:
        revised = _list_revised_references(run_process, facts)
        findings.extend(
            f"{path} is the REFERENCE {target} is judged against, and its branch changes it:"
            " a task delivering its reference says so with REVISES at the base of its branch"
            for path in changed
            if path not in revised
        )
    return judge_findings(NAME, findings)
