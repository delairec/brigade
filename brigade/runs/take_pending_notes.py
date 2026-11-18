from pathlib import Path

from brigade.runs.list_notes import PENDING, list_notes
from brigade.runs.run_locations import CARRIED_NOTES_FILE, SEGMENTS_DIRECTORY
from brigade.system.write_json_atomically import write_json_atomically


def take_pending_notes(run_directory: Path, segment: int) -> list[dict]:
    pending = [note for note in list_notes(run_directory) if note["segment"] is PENDING]
    write_json_atomically(
        run_directory / SEGMENTS_DIRECTORY / str(segment) / CARRIED_NOTES_FILE, {"carried": len(pending)}
    )
    return [{"at": note["at"], "text": note["text"]} for note in pending]
