import json
import shutil
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tests.awawa.list_temporary_roots import list_temporary_roots
from tests.awawa.volatile_value_masker import (
    COMMIT_PLACEHOLDER,
    INSTANT_PLACEHOLDER,
    PLACEHOLDER,
    RUN_PLACEHOLDER,
    VolatileValueMasker,
)
from tests.process_launcher import ProcessLauncher

UNREADABLE = 0
REPLAYED_INSTANT = datetime(2026, 1, 1, tzinfo=UTC)
INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
COMMIT_NAME_FORMAT = "040x"
RUN_INSTANT_FORMAT = "%Y%m%dT%H%M%SZ"
RUN_ID_SEPARATORS = {"run": "-", "run_name": "_"}


def _create_temporary_directory(test_case: unittest.TestCase) -> str:
    directory = tempfile.mkdtemp()
    test_case.addCleanup(shutil.rmtree, directory)
    return directory


def _read_input(file: Path) -> str | None:
    try:
        return file.read_text()
    except PermissionError:
        return None


def _write_input(file: Path, content: str | None) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content or "")
    if content is None:
        file.chmod(UNREADABLE)


def _replay_instant(number: str) -> str:
    return (REPLAYED_INSTANT + timedelta(seconds=int(number))).strftime(INSTANT_FORMAT)


def _replay_commit_name(number: str) -> str:
    return format(int(number), COMMIT_NAME_FORMAT)


def _replay_run_id(kind: str, number: str) -> str:
    separator = RUN_ID_SEPARATORS[kind]
    return f"{REPLAYED_INSTANT.strftime(RUN_INSTANT_FORMAT)}{separator}{int(number):06x}"


def replay_recording(test_case: unittest.TestCase, call: dict) -> dict:
    recorded = json.dumps(call)
    placeholders = sorted(set(PLACEHOLDER.findall(recorded)), key=int)
    known = {f"<tmp:{number}>": _create_temporary_directory(test_case) for number in placeholders}
    known.update({f"<instant:{number}>": _replay_instant(number) for number in INSTANT_PLACEHOLDER.findall(recorded)})
    known.update({f"<commit:{number}>": _replay_commit_name(number) for number in COMMIT_PLACEHOLDER.findall(recorded)})
    known.update(
        {f"<{kind}:{number}>": _replay_run_id(kind, number) for kind, number in RUN_PLACEHOLDER.findall(recorded)}
    )
    masker = VolatileValueMasker(list_temporary_roots(), known)
    for directory in call["directories"]:
        Path(masker.unmask(directory)).mkdir(parents=True, exist_ok=True)
    inputs = {Path(masker.unmask(path)): content for path, content in call["inputs"].items()}
    for file, content in inputs.items():
        _write_input(file, None if content is None else masker.unmask(content))
    cwd = Path(masker.unmask(call["cwd"]))
    cwd.mkdir(parents=True, exist_ok=True)
    before = {file: _read_input(file) for file in inputs}
    completed = ProcessLauncher.run(
        ["awawa", *(masker.unmask(argument) for argument in call["arguments"])],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "stdout": masker.mask(completed.stdout),
        "stderr": masker.mask(completed.stderr),
        "exit_code": completed.returncode,
        "rewritten": {
            masker.mask(str(file)): masker.mask(_read_input(file) or "")
            for file in inputs
            if _read_input(file) != before[file]
        },
    }
