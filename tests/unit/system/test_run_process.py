import unittest

from brigade.errors import ToolFailure
from brigade.system.run_process import ProcessRequest, run_process


class RunProcessPastItsTimeoutTest(unittest.TestCase):
    def test_should_refuse_naming_the_command_and_its_timeout(self):
        # Arrange
        request = ProcessRequest(argv=("sleep", "30"), cwd="/", timeout_s=0.1)

        # Act
        with self.assertRaises(ToolFailure) as refusal:
            run_process(request)

        # Assert
        self.assertEqual(str(refusal.exception), "sleep 30 timed out after 0.1 s")
