import unittest

from brigade.runs.compose_brief import BriefParts, compose_brief


class ComposeBriefTest(unittest.TestCase):
    def test_should_lay_out_every_section_given_in_its_order(self):
        # Arrange
        parts = BriefParts(
            progress="Step one is done.\n",
            procedure="build-task",
            procedure_body="Deliver the task.",
            arguments={"task": "@TASK.B1", "base": "main"},
            brief="Start from the base.",
            progress_description="Keep your progress in /state/progress.md.",
            budget=132,
        )

        # Act
        brief = compose_brief(parts)

        # Assert
        self.assertEqual(
            brief,
            "# Progress so far\n\nStep one is done.\n\n"
            "# Procedure build-task\n\nDeliver the task.\n\n"
            "# Arguments\n\ntask=@TASK.B1\nbase=main\n\n"
            "# Brief\n\nStart from the base.\n\n"
            "# Progress file\n\nKeep your progress in /state/progress.md.\n\n"
            "# Budget\n\n132 steps, the cap of your role for this segment.\n\n"
            "# End of segment\n\nEnd your final message on one of these lines: brigade-end: done once the work is"
            " delivered, brigade-end: handed_over when a next segment resumes it from the progress file,"
            " brigade-end: blocked when it waits for a ruling.\n",
        )
