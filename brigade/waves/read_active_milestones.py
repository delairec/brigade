from collections.abc import Callable
from pathlib import Path

from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.system.run_process import ProcessRecord, ProcessRequest

MILESTONE = "MILESTONE"
MILESTONE_PREFIX = "@MILESTONE."
STATUS_FIELD = "STATUS"
ACTIVE_STATUS = "active"


def read_active_milestones(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path) -> frozenset[str]:
    status = read_awawa_document(
        run_process, root, ("status", MILESTONE, "--where", f"{STATUS_FIELD}=={ACTIVE_STATUS}")
    )
    return frozenset(MILESTONE_PREFIX + entity["name"] for entity in status["entities"])
