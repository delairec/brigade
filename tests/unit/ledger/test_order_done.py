import unittest

from brigade.ledger.order_done import OrderDone


class OrderDoneTest(unittest.TestCase):
    def test_should_read_the_order_done_for_a_project(self):
        # Act
        event = OrderDone.from_document({"event": "order.done", "project": "tidepool", "kind": "study"})

        # Assert
        self.assertEqual(event, OrderDone(project="tidepool", kind="study"))

    def test_should_write_back_the_document_it_reads(self):
        # Arrange
        document = {"project": "tidepool", "kind": "sweep", "order": "o1", "run": "20261010T090000Z-b86a01"}

        # Act
        written = OrderDone.from_document(document).to_document()

        # Assert
        self.assertEqual(
            written, {"project": "tidepool", "kind": "sweep", "order": "o1", "run": "20261010T090000Z-b86a01"}
        )
