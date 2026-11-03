import json
import os
import shutil
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from tests.awawa.list_temporary_roots import list_temporary_roots
from tests.process_launcher import ProcessLauncher

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RealAwawa:
    path: str
    records: bool


def _read_version(real_awawa: RealAwawa | None) -> str | None:
    if real_awawa is None:
        return None
    completed = ProcessLauncher.run([real_awawa.path, "--version"], capture_output=True, text=True, check=True)
    return completed.stdout.strip()


def _fail_on_misses(test_case: unittest.TestCase, misses: Path) -> None:
    if misses.exists():
        test_case.fail(
            f"{misses.read_text()}record the calls with awawa on PATH:"
            f" AWAWA_RECORD=1 python3 -m unittest {test_case.id()}"
        )


def install_fake_awawa(
    test_case: unittest.TestCase, recordings: Path, real_awawa: RealAwawa | None, search_path: str
) -> str:
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
                "real_awawa": None if real_awawa is None else real_awawa.path,
                "records": real_awawa is not None and real_awawa.records,
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
