import json
from pathlib import Path

from tests.unit.recording_process_runner import ProcessAnswer


def create_registry_answers(config_root: Path, projects: dict[str, dict[str, str]]) -> dict:
    root = str(config_root)
    status = {"entities": [{"type": "PROJECT", "name": name} for name in projects]}
    shown = {
        ("awawa", "show", f"@PROJECT.{name}", "--json", root): ProcessAnswer(
            stdout=json.dumps(
                {"fields": [{"name": key, "atoms": [json.dumps(value)]} for key, value in fields.items()]}
            )
        )
        for name, fields in projects.items()
    }
    return {("awawa", "status", "PROJECT", "--json", root): ProcessAnswer(stdout=json.dumps(status)), **shown}
