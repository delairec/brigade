import unittest

from brigade.ledger.run_noted import RunNoted


class RunNotedTest(unittest.TestCase):
    def test_should_read_the_run_and_the_text_of_the_note(self):
        # Act
        event = RunNoted.from_document(
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "run.noted",
                "run": "20261007T090000Z-b70a01",
                "text": "the corpus of main holds two L016 errors",
            }
        )

        # Assert
        self.assertEqual(
            event, RunNoted(run="20261007T090000Z-b70a01", text="the corpus of main holds two L016 errors")
        )

    def test_should_write_the_run_and_the_text_of_the_note(self):
        # Arrange
        event = RunNoted(run="20261007T090000Z-b70a01", text="the corpus of main holds two L016 errors")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document, {"run": "20261007T090000Z-b70a01", "text": "the corpus of main holds two L016 errors"}
        )
