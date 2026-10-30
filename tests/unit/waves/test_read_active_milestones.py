import unittest
from pathlib import Path

from brigade.waves.read_active_milestones import read_active_milestones
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class ReadActiveMilestonesTest(unittest.TestCase):
    def test_should_name_each_active_milestone_of_the_corpus_by_its_reference(self):
        # Arrange
        awawa = RecordingProcessRunner(
            {
                ("awawa", "status", "MILESTONE", "--where", "STATUS==active", "--json", "/srv/shop"): ProcessAnswer(
                    stdout='{"entities": [{"name": "M3"}, {"name": "M9"}]}'
                )
            }
        )

        # Act
        milestones = read_active_milestones(awawa, Path("/srv/shop"))

        # Assert
        self.assertEqual(milestones, frozenset({"@MILESTONE.M3", "@MILESTONE.M9"}))
