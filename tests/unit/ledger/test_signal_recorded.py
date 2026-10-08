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

    def test_should_write_back_the_signal_of_a_run_given_no_project(self):
        # Arrange
        document = {**SIGNAL_OF_A_PROJECT_RUN, "project": None}

        # Act
        project = SignalRecorded.from_document(document).to_document()["project"]

        # Assert
        self.assertIsNone(project)
