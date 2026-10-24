import contextlib
import fcntl
import io
import os
import tempfile
import unittest
from pathlib import Path
from typing import TextIO

from brigade.errors import BrigadeError
from brigade.system.hold_lock import hold_lock
from tests.unit.system.try_lock import try_lock


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


class StderrReleasingTheHolderDouble:
    def __init__(self, holder: TextIO):
        self.holder = holder
        self.lines = []

    def write(self, text: str) -> int:
        self.lines.append(text)
        fcntl.flock(self.holder, fcntl.LOCK_UN)
        return len(text)

    def flush(self) -> None:
        pass


class HoldLockHeldByAnotherProcessTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.lock_path = Path(self.root.name) / "corpus.lock"
        self.lock_path.write_text("4242\n")
        self.holder = self.lock_path.open("a")
        self.addCleanup(self.holder.close)
        fcntl.flock(self.holder, fcntl.LOCK_EX)

    def test_should_announce_the_wait_naming_the_lock_and_its_holder(self):
        # Arrange
        stderr = StderrReleasingTheHolderDouble(self.holder)

        # Act
        self.enter_the_lock(stderr)

        # Assert
        self.assertEqual(stderr.lines, [f"brigade: waiting for the lock {self.lock_path}, held by pid 4242\n"])

    def test_should_write_its_pid_over_the_one_of_the_holder_it_waited_for(self):
        # Arrange
        stderr = StderrReleasingTheHolderDouble(self.holder)

        # Act
        content = self.enter_the_lock(stderr)

        # Assert
        self.assertEqual(content, f"{os.getpid()}\n")

    def test_should_exclude_every_other_holder_once_the_other_process_released_it(self):
        # Arrange
        stderr = StderrReleasingTheHolderDouble(self.holder)

        # Act
        acquired_by_another = self.try_lock_inside_the_lock(stderr)

        # Assert
        self.assertFalse(acquired_by_another)

    def enter_the_lock(self, stderr: StderrReleasingTheHolderDouble) -> str:
        with contextlib.redirect_stderr(stderr), hold_lock(self.lock_path):
            return self.lock_path.read_text()

    def try_lock_inside_the_lock(self, stderr: StderrReleasingTheHolderDouble) -> bool:
        with contextlib.redirect_stderr(stderr), hold_lock(self.lock_path):
            return try_lock(self.lock_path)


class HoldLockLeftFreeTest(unittest.TestCase):
    def test_should_write_nothing_on_stderr(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        stderr = io.StringIO()

        # Act
        with contextlib.redirect_stderr(stderr), hold_lock(Path(root.name) / "corpus.lock"):
            pass

        # Assert
        self.assertEqual(stderr.getvalue(), "")


class HoldLockWhereTheMachineRefusesTheWriteTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.locks = Path(self.root.name) / "state" / "locks"
        self.lock_path = self.locks / "corpus.lock"

    def test_should_name_the_directory_it_cannot_create(self):
        # Arrange
        self.locks.parent.mkdir()
        self.locks.touch()

        # Act
        with self.assertRaises(BrigadeError) as refusal, hold_lock(self.lock_path):
            pass

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.locks}: File exists")

    def test_should_name_the_lock_it_cannot_open(self):
        # Arrange
        self.lock_path.mkdir(parents=True)

        # Act
        with self.assertRaises(BrigadeError) as refusal, hold_lock(self.lock_path):
            pass

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.lock_path}: Is a directory")


class HoldLockOnADeviceRefusingEveryWriteTest(unittest.TestCase):
    def test_should_name_the_lock_it_cannot_write_its_pid_in(self):
        # Arrange
        device_full = Path("/dev/full")

        # Act
        with self.assertRaises(BrigadeError) as refusal, hold_lock(device_full):
            pass

        # Assert
        self.assertEqual(str(refusal.exception), "cannot write /dev/full: Invalid argument")
