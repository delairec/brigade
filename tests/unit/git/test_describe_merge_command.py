import unittest
from pathlib import Path

from brigade.git.describe_merge_command import describe_merge_command


class DescribeMergeCommandTest(unittest.TestCase):
    def test_should_print_the_command_a_user_can_paste(self):
        for repository, expected in [
            (Path("/srv/app"), "git -C /srv/app merge corpus"),
            (Path("/srv/my app"), "git -C '/srv/my app' merge corpus"),
        ]:
            with self.subTest(repository=repository):
                # Act
                command = describe_merge_command(repository, "corpus")

                # Assert
                self.assertEqual(command, expected)
