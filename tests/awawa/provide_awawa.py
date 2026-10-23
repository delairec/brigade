import os
import unittest
from pathlib import Path

from tests.awawa.provide_awawa_from import provide_awawa_from

RECORDINGS = Path(__file__).resolve().parent / "recordings"


def provide_awawa(test_case: unittest.TestCase) -> str:
    return provide_awawa_from(test_case, os.environ, RECORDINGS)
