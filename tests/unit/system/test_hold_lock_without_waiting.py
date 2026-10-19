import fcntl
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.hold_lock_without_waiting import hold_lock_without_waiting


def try_lock(path: Path) -> bool:
    with path.open("a") as other_holder:
        try:
            fcntl.flock(other_holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True


class HoldLockWithoutWaitingTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.lock_path = Path(self.root.name) / "locks" / "tick.lock"

    def tearDown(self):
        self.root.cleanup()

    def test_should_take_a_free_lock_and_exclude_every_other_holder(self):
        # Act
        with hold_lock_without_waiting(self.lock_path) as acquired:
            acquired_by_another = try_lock(self.lock_path)

        # Assert
        self.assertEqual((acquired, acquired_by_another), (True, False))

    def test_should_give_up_at_once_when_another_holds_the_lock(self):
        # Arrange
        self.lock_path.parent.mkdir()
        other_holder = self.enterContext(self.lock_path.open("a"))
        fcntl.flock(other_holder, fcntl.LOCK_EX)

        # Act
        with hold_lock_without_waiting(self.lock_path) as acquired:
            pass

        # Assert
        self.assertFalse(acquired)

    def test_should_release_the_lock_on_exit(self):
        # Arrange
        with hold_lock_without_waiting(self.lock_path):
            pass

        # Act
        acquired_by_another = try_lock(self.lock_path)

        # Assert
        self.assertTrue(acquired_by_another)


class HoldLockWithoutWaitingWhereTheMachineRefusesTheWriteTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.locks = Path(self.root.name) / "state" / "locks"
        self.lock_path = self.locks / "tick.lock"

    def test_should_name_the_directory_it_cannot_create(self):
        # Arrange
        self.locks.parent.mkdir()
        self.locks.touch()

        # Act
        with self.assertRaises(BrigadeError) as refusal, hold_lock_without_waiting(self.lock_path):
            pass

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.locks}: File exists")

    def test_should_name_the_lock_it_cannot_open(self):
        # Arrange
        self.lock_path.mkdir(parents=True)

        # Act
        with self.assertRaises(BrigadeError) as refusal, hold_lock_without_waiting(self.lock_path):
            pass

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.lock_path}: Is a directory")


@unittest.skipUnless(Path("/dev/full").exists(), "no device refusing every write")
class HoldLockWithoutWaitingOnADeviceRefusingEveryWriteTest(unittest.TestCase):
    def test_should_name_the_lock_it_cannot_write_its_pid_in(self):
        # Arrange
        device_full = Path("/dev/full")

        # Act
        with self.assertRaises(BrigadeError) as refusal, hold_lock_without_waiting(device_full):
            pass

        # Assert
        self.assertEqual(str(refusal.exception), "cannot write /dev/full: Invalid argument")
