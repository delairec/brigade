import errno
import unittest
from pathlib import Path

from brigade.errors import CannotWrite
from brigade.system.refuse_failed_write import refuse_failed_write

CACHE = Path("/srv/refs")


class RefuseFailedWriteTest(unittest.TestCase):
    def test_should_name_the_path_the_failure_names(self):
        # Act
        with self.assertRaises(CannotWrite) as refusal, refuse_failed_write(CACHE):
            raise PermissionError(errno.EACCES, "Permission denied", "/srv/refs/shop/abc123")

        # Assert
        self.assertEqual(str(refusal.exception), "cannot write /srv/refs/shop/abc123: Permission denied")

    def test_should_name_the_path_it_was_given_when_the_failure_names_none(self):
        # Act
        with self.assertRaises(CannotWrite) as refusal, refuse_failed_write(CACHE):
            raise OSError(errno.EIO, "Input/output error")

        # Assert
        self.assertEqual(str(refusal.exception), "cannot write /srv/refs: Input/output error")

    def test_should_let_a_block_that_does_not_fail_answer(self):
        # Act
        with refuse_failed_write(CACHE):
            answer = "abc123"

        # Assert
        self.assertEqual(answer, "abc123")
