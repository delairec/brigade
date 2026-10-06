import json
from pathlib import Path

from brigade.system.write_text_atomically import write_text_atomically


def write_json_atomically(path: Path, document: dict) -> None:
    write_text_atomically(path, json.dumps(document) + "\n")
