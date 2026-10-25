from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.check_ancestor import check_ancestor
from brigade.git.find_merge_base import find_merge_base
from brigade.git.read_diff import read_diff
from brigade.git.read_range_diff import read_range_diff
from brigade.system.run_process import ProcessRecord, ProcessRequest

ANCESTOR = 0


@dataclass(frozen=True)
class RepairSpan:
    repository: Path
    wave_head: str
    judged_head: str
    head: str
    base: str


def read_repair_diff(run_process: Callable[[ProcessRequest], ProcessRecord], span: RepairSpan) -> ProcessRecord:
    if check_ancestor(run_process, span.repository, span.judged_head, span.head).exit_code == ANCESTOR:
        return read_diff(run_process, span.repository, span.judged_head, span.head)
    judged_base = find_merge_base(run_process, span.repository, span.wave_head, span.judged_head)
    return read_range_diff(
        run_process, span.repository, f"{judged_base}..{span.judged_head}", f"{span.base}..{span.head}"
    )
