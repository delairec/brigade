import unittest

from brigade.errors import ToolNotFound
from brigade.system.find_awawa_web import find_awawa_web
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner


class FindAwawaWebTest(unittest.TestCase):
    def test_should_tell_whether_awawa_web_is_on_the_path(self):
        # Arrange
        rows = [("absent", ToolNotFound("awawa-web"), False), ("on the PATH", ProcessAnswer(), True)]
        for case, answer, expected in rows:
            with self.subTest(case=case):
                runner = ScriptedProcessRunner({("awawa-web", "--help"): answer})

                # Act
                found = find_awawa_web(runner.run)

                # Assert
                self.assertIs(found, expected)
