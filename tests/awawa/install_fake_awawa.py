import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from tests.awawa.list_temporary_roots import list_temporary_roots
from tests.process_launcher import ProcessLauncher

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _read_version(real_awawa: str | None) -> str | None:
    if real_awawa is None:
        return None
    completed = ProcessLauncher.run([real_awawa, "--version"], capture_output=True, text=True, check=True)
    return completed.stdout.strip()


def _fail_on_misses(test_case: unittest.TestCase, misses: Path) -> None:
    if misses.exists():
        test_case.fail(misses.read_text())


def install_fake_awawa(test_case: unittest.TestCase, recordings: Path, real_awawa: str | None, search_path: str) -> str:
    directory = Path(tempfile.mkdtemp())
    test_case.addCleanup(shutil.rmtree, directory)
    configuration = directory / "configuration.json"
    misses = directory / "misses.txt"
    configuration.write_text(
        json.dumps(
            {
                "recordings": str(recordings),
                "temporary_roots": list_temporary_roots(),
                "misses": str(misses),
                "real_awawa": real_awawa,
                "version": _read_version(real_awawa),
            }
        )
    )
    executable = directory / "awawa"
    executable.write_text(
        f'#!/bin/sh\nPYTHONPATH="{REPOSITORY_ROOT}" exec "{sys.executable}" -m tests.awawa.replay_awawa'
        f' "{configuration}" "$@"\n'
    )
    executable.chmod(0o755)
    test_case.addCleanup(_fail_on_misses, test_case, misses)
    return f"{directory}{os.pathsep}{search_path}"
