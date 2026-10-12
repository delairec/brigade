import unittest

from brigade.ledger.signal_recorded import SignalRecorded

SIGNAL_OF_A_PROJECT_RUN = {
    "signal": "budget_reached",
    "project": "tidepool",
    "procedure": "deliver",
    "run": "20261008T090000Z-b74a01",
    "segment": 1,
    "budget": 40,
}


class SignalRecordedTest(unittest.TestCase):
    def test_should_write_back_the_signal_of_a_project_run(self):
        # Act
        document = SignalRecorded.from_document(SIGNAL_OF_A_PROJECT_RUN).to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "signal": "budget_reached",
                "project": "tidepool",
                "procedure": "deliver",
                "run": "20261008T090000Z-b74a01",
                "segment": 1,
                "budget": 40,
            },
        )

    def test_should_write_back_the_limit_of_a_segment_cut_on_the_clock(self):
        # Arrange
        document = {**SIGNAL_OF_A_PROJECT_RUN, "signal": "wall_limit_reached", "wall_limit_s": 1500}

        # Act
        written = SignalRecorded.from_document(document).to_document()

        # Assert
        self.assertEqual(
            written,
            {
                "signal": "wall_limit_reached",
                "project": "tidepool",
                "procedure": "deliver",
                "run": "20261008T090000Z-b74a01",
                "segment": 1,
                "budget": 40,
                "wall_limit_s": 1500,
            },
        )

    def test_should_write_back_the_steps_of_a_segment_over_its_budget(self):
        # Arrange
        document = {**SIGNAL_OF_A_PROJECT_RUN, "signal": "budget_exceeded", "steps": 57}

        # Act
        written = SignalRecorded.from_document(document).to_document()

        # Assert
        self.assertEqual(
            written,
            {
                "signal": "budget_exceeded",
                "project": "tidepool",
                "procedure": "deliver",
                "run": "20261008T090000Z-b74a01",
                "segment": 1,
                "budget": 40,
                "steps": 57,
            },
        )

    def test_should_write_back_the_signal_of_a_run_given_no_project(self):
        # Arrange
        document = {**SIGNAL_OF_A_PROJECT_RUN, "project": None}

        # Act
        project = SignalRecorded.from_document(document).to_document()["project"]

        # Assert
        self.assertIsNone(project)
