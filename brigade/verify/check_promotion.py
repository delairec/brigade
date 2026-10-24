from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.collect_anchors import collect_anchors
from brigade.corpus.decode_atom import decode_atom
from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.verify.judge_findings import judge_findings

NAME = "promotion"
IMPLEMENTED = "implemented"
ANCHOR_SEPARATOR = "::"
NO_PULL_REQUEST = "no pull request"


@dataclass(frozen=True)
class PromotionFacts:
    head_tree: Path
    task: str
    pr: int


def _read_atom(field: dict) -> str:
    atom = field["atoms"][0]
    return decode_atom(atom)


def _read_value(fields: list, name: str) -> str | None:
    return next((_read_atom(field) for field in fields if field["name"] == name), None)


def _resolves(head_tree: Path, anchor: str) -> bool:
    path, _separator, text = anchor.partition(ANCHOR_SEPARATOR)
    file = head_tree / path
    return file.is_file() and text in file.read_text(encoding="utf-8", errors="replace")


def check_promotion(run_process: Callable[[ProcessRequest], ProcessRecord], facts: PromotionFacts) -> dict:
    target = f"@TASK.{facts.task}"
    fields = read_awawa_document(run_process, facts.head_tree, ("show", target))["fields"]
    findings = []
    status = _read_value(fields, "STATUS")
    if status != IMPLEMENTED:
        findings.append(f"{target} is STATUS {status}, not implemented")
    delivered_by = _read_value(fields, "DELIVERED_BY")
    if delivered_by != str(facts.pr):
        findings.append(
            f"{target} is delivered by {f'#{delivered_by}' if delivered_by else NO_PULL_REQUEST}, not by #{facts.pr}"
        )
    specs = [field for field in fields if field["name"] == "SPEC"]
    for rank, spec in enumerate(specs, start=1):
        if not any(_resolves(facts.head_tree, anchor) for anchor in collect_anchors(spec["fields"])):
            findings.append(f"SPEC {rank} has no IMPL whose anchor resolves: {_read_atom(spec)}")
    return judge_findings(NAME, findings)
