import unittest

from brigade.ledger.order_parked import OrderParked


class OrderParkedTest(unittest.TestCase):
    def test_should_write_back_the_document_it_reads(self):
        # Arrange
        document = {"project": "shop", "kind": "sweep", "order": "o1", "run": "r1", "step": "verify", "reason": "red"}

        # Act
        written = OrderParked.from_document(document).to_document()

        # Assert
        self.assertEqual(
            written, {"project": "shop", "kind": "sweep", "order": "o1", "run": "r1", "step": "verify", "reason": "red"}
        )
