from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.check_ancestor import check_ancestor
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.verify.judge_findings import judge_findings

NAME = "ancestry"
DESCENDS = 0


@dataclass(frozen=True)
class AncestryFacts:
    repository: Path
    wave_branch: str
    wave_head: str
    head: str


def check_ancestry(run_process: Callable[[ProcessRequest], ProcessRecord], facts: AncestryFacts) -> dict:
    record = check_ancestor(run_process, facts.repository, facts.wave_head, facts.head)
    if record.exit_code == DESCENDS:
        return judge_findings(NAME, [])
    return judge_findings(NAME, [f"{facts.head} does not descend from {facts.wave_branch} at {facts.wave_head}"])
