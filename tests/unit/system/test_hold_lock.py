import fcntl
import os
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.hold_lock import hold_lock


def try_lock(path: Path) -> bool:
    with open(path, "a") as other_holder:
        try:
            fcntl.flock(other_holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True


class HoldLockTest(unittest.TestCase):
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

    def test_should_let_an_error_raised_while_held_through_as_it_is(self):
        # Arrange
        refused_elsewhere = PermissionError(13, "Permission denied", "/srv/elsewhere")

        # Act
        with self.assertRaises(PermissionError) as raised, hold_lock(self.lock_path):
            raise refused_elsewhere

        # Assert
        self.assertIs(raised.exception, refused_elsewhere)


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class HoldLockWhereTheMachineRefusesTheWriteTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.state = Path(self.root.name) / "state"
        self.state.mkdir()
        self.addCleanup(self.state.chmod, 0o700)
        self.locks = self.state / "locks"
        self.lock_path = self.locks / "corpus.lock"

    def test_should_name_the_directory_it_cannot_create(self):
        # Arrange
        self.state.chmod(0o500)

        # Act
        with self.assertRaises(BrigadeError) as refusal, hold_lock(self.lock_path):
            pass

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.locks}: Permission denied")

    def test_should_name_the_lock_it_cannot_open(self):
        # Arrange
        self.locks.mkdir()
        self.lock_path.touch(mode=0o400)

        # Act
        with self.assertRaises(BrigadeError) as refusal, hold_lock(self.lock_path):
            pass

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.lock_path}: Permission denied")
