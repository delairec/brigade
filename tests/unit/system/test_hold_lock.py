import os
import tempfile
import unittest
from pathlib import Path

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
