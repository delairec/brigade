import unittest
from pathlib import Path

from brigade.verify.check_ancestry import AncestryFacts, check_ancestry
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

FACTS = AncestryFacts(repository=Path("/srv/shop"), wave_branch="integration/w1", wave_head="1111111", head="2222222")
IS_ANCESTOR = ("git", "merge-base", "--is-ancestor", "1111111", "2222222")


class CheckAncestryTest(unittest.TestCase):
    def test_should_pass_a_head_descending_from_the_wave_branch(self):
        # Act
        check = check_ancestry(RecordingProcessRunner(), FACTS)

        # Assert
        self.assertEqual(check, {"name": "ancestry", "verdict": "pass", "findings": []})

    def test_should_fail_a_head_off_the_wave_branch(self):
        # Arrange
        git = RecordingProcessRunner({IS_ANCESTOR: ProcessAnswer(exit_code=1)})

        # Act
        check = check_ancestry(git, FACTS)

        # Assert
        self.assertEqual(
            check,
            {
                "name": "ancestry",
                "verdict": "fail",
                "findings": ["2222222 does not descend from integration/w1 at 1111111"],
            },
        )
