import os
import shutil
import unittest
from pathlib import Path

from tests.awawa.install_fake_awawa import install_fake_awawa

RECORDINGS = Path(__file__).resolve().parent / "recordings"
RECORD_VARIABLE = "AWAWA_RECORD"


def provide_awawa(test_case: unittest.TestCase) -> None:
    real_awawa = shutil.which("awawa")
    recording = os.environ.get(RECORD_VARIABLE) == "1"
    if real_awawa is None or recording:
        install_fake_awawa(test_case, RECORDINGS, real_awawa if recording else None)
