import unittest

from brigade.ledger.step_done import StepDone


class StepDoneTest(unittest.TestCase):
    def test_should_write_back_the_document_it_reads(self):
        # Arrange
        document = {"kind": "sweep", "run": "r1", "step": "verify"}

        # Act
        written = StepDone.from_document(document).to_document()

        # Assert
        self.assertEqual(written, {"kind": "sweep", "run": "r1", "step": "verify"})
