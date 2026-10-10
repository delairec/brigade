import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.awawa.list_temporary_roots import list_temporary_roots
from tests.awawa.volatile_value_masker import PLACEHOLDER, VolatileValueMasker

UNREADABLE = 0


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


def replay_recording(test_case: unittest.TestCase, call: dict) -> dict:
    placeholders = sorted(set(PLACEHOLDER.findall(json.dumps(call))), key=int)
    known = {f"<tmp:{number}>": _create_temporary_directory(test_case) for number in placeholders}
    masker = VolatileValueMasker(list_temporary_roots(), known)
    for directory in call["directories"]:
        Path(masker.unmask(directory)).mkdir(parents=True, exist_ok=True)
    inputs = {Path(masker.unmask(path)): content for path, content in call["inputs"].items()}
    for file, content in inputs.items():
        _write_input(file, None if content is None else masker.unmask(content))
    cwd = Path(masker.unmask(call["cwd"]))
    cwd.mkdir(parents=True, exist_ok=True)
    before = {file: _read_input(file) for file in inputs}
    completed = subprocess.run(  # noqa: S603 - the recorded call
        ["awawa", *(masker.unmask(argument) for argument in call["arguments"])],  # noqa: S607 - the awawa on the PATH
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
