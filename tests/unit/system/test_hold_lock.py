import fcntl
import os
import tempfile
import unittest
from pathlib import Path

from brigade.system.hold_lock import hold_lock


def try_lock(path: Path) -> bool:
    with open(path, "a") as other_holder:
        try:
            fcntl.flock(other_holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True


class HoldLock(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.lock_path = Path(self.root.name) / "locks" / "corpus.lock"

    def tearDown(self):
        self.root.cleanup()

    def test_should_exclude_every_other_holder_while_held(self):
        # Act
        with hold_lock(self.lock_path):
            acquired_by_another = try_lock(self.lock_path)

        # Assert
        self.assertFalse(acquired_by_another)

    def test_should_release_the_lock_on_exit(self):
        # Arrange
        with hold_lock(self.lock_path):
            pass

        # Act
        acquired_by_another = try_lock(self.lock_path)

        # Assert
        self.assertTrue(acquired_by_another)

    def test_should_write_the_pid_of_the_holder_for_diagnosis(self):
        # Act
        with hold_lock(self.lock_path):
            content = self.lock_path.read_text()

        # Assert
        self.assertEqual(content, f"{os.getpid()}\n")
