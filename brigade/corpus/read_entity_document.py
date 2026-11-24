import json
from collections.abc import Callable
from pathlib import Path

from brigade.corpus.read_entity import ENTITY_NOT_SHOWN, SHOWN_OR_NOT, UNKNOWN_ENTITY_DIAGNOSTIC
from brigade.corpus.run_awawa import run_awawa
from brigade.errors import CommandFailed
from brigade.system.run_process import ProcessRecord, ProcessRequest


def read_entity_document(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, target: str
) -> dict | None:
    record = run_awawa(run_process, root, ("show", target, "--json", str(root)), SHOWN_OR_NOT)
    if record.exit_code != ENTITY_NOT_SHOWN:
        return json.loads(record.stdout)
    if UNKNOWN_ENTITY_DIAGNOSTIC in record.stderr:
        return None
    raise CommandFailed(record.argv, record.exit_code, record.stderr)
