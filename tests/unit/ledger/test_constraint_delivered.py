import unittest

from brigade.ledger.constraint_delivered import ConstraintDelivered


class ConstraintDeliveredTest(unittest.TestCase):
    def test_should_read_the_constraint_delivered_for_a_project(self):
        # Act
        event = ConstraintDelivered.from_document({"event": "constraint.delivered", "project": "tidepool"})

        # Assert
        self.assertEqual(event, ConstraintDelivered(project="tidepool"))
