import fcntl
import tempfile
import unittest
from pathlib import Path

from brigade.system.hold_lock_without_waiting import hold_lock_without_waiting


def try_lock(path: Path) -> bool:
    with open(path, "a") as other_holder:
        try:
            fcntl.flock(other_holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True


class HoldLockWithoutWaiting(unittest.TestCase):
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
        other_holder = open(self.lock_path, "a")
        self.addCleanup(other_holder.close)
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
