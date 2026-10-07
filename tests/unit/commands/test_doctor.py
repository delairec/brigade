import unittest

from brigade.commands.doctor import AWAWA_FLOOR, _read_release


class ReadReleaseTest(unittest.TestCase):
    def test_should_read_the_release_of_a_version(self):
        # Act
        release = _read_release("2.7.1")

        # Assert
        self.assertEqual(release, AWAWA_FLOOR)

    def test_should_read_only_the_first_parts_of_a_long_version(self):
        # Act
        release = _read_release("2.7.1.4")

        # Assert
        self.assertEqual(release, AWAWA_FLOOR)

    def test_should_return_none_when_a_part_is_not_a_number(self):
        # Act
        release = _read_release("2.x")

        # Assert
        self.assertIsNone(release)
