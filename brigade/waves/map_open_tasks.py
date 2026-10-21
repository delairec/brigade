from brigade.ledger.ledger_entry import LedgerEntry
from brigade.waves.list_open_waves import list_open_waves


def map_open_tasks(entries: tuple[LedgerEntry, ...], project: str) -> dict[str, str]:
    return {task: wave.wave for wave in list_open_waves(entries, project) for task in wave.tasks}
