import unittest

from brigade.registry.locate_project_block import locate_project_block


class LocateProjectBlockTest(unittest.TestCase):
    def test_should_find_the_block_of_the_project(self):
        # Arrange
        lines = [
            "PROJECT alpha\n",
            '\tPATH "/srv/alpha"\n',
            "\n",
            "PROJECT beta\n",
            '\tPATH "/srv/beta"\n',
        ]

        # Act
        block = locate_project_block(lines, "beta")

        # Assert
        self.assertEqual(block, range(3, 5))

    def test_should_return_none_when_no_project_matches(self):
        # Arrange
        lines = ["PROJECT alpha\n", '\tPATH "/srv/alpha"\n']

        # Act
        block = locate_project_block(lines, "gamma")

        # Assert
        self.assertIsNone(block)

    def test_should_skip_lines_that_do_not_match_the_header(self):
        # Arrange
        lines = [
            "DECISION D1\n",
            '\tTITLE "something"\n',
            "PROJECT alpha\n",
            '\tPATH "/srv/alpha"\n',
        ]

        # Act
        block = locate_project_block(lines, "alpha")

        # Assert
        self.assertEqual(block, range(2, 4))
