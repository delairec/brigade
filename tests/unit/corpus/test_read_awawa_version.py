import unittest

from brigade.corpus.read_awawa_version import read_awawa_version
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class ReadAwawaVersionTest(unittest.TestCase):
    def test_should_answer_the_bare_version_number(self):
        # Arrange
        awawa = RecordingProcessRunner({("awawa", "--version"): ProcessAnswer(stdout="awawa 2.4.1\n")})

        # Act
        version = read_awawa_version(awawa)

        # Assert
        self.assertEqual(version, "2.4.1")
