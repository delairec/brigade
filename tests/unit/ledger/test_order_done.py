import unittest

from brigade.ledger.order_done import OrderDone


class OrderDoneTest(unittest.TestCase):
    def test_should_read_the_order_done_for_a_project(self):
        # Act
        event = OrderDone.from_document({"event": "order.done", "project": "tidepool", "kind": "study"})

        # Assert
        self.assertEqual(event, OrderDone(project="tidepool", kind="study"))
