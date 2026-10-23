import shutil
import unittest
from collections.abc import Mapping
from pathlib import Path

from tests.awawa.install_fake_awawa import install_fake_awawa

RECORD_VARIABLE = "AWAWA_RECORD"


def provide_awawa_from(test_case: unittest.TestCase, environment: Mapping[str, str], recordings: Path) -> str:
    search_path = environment["PATH"]
    real_awawa = shutil.which("awawa", path=search_path)
    recording = environment.get(RECORD_VARIABLE) == "1"
    if real_awawa is None or recording:
        return install_fake_awawa(test_case, recordings, real_awawa if recording else None, search_path)
    return search_path
