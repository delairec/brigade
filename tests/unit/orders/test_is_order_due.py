import unittest
from datetime import UTC, datetime

from brigade.errors import BrigadeError
from brigade.orders.is_order_due import OrderFacts, is_order_due

NOW = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)
AN_HOUR_AGO = datetime(2026, 10, 19, 8, 0, tzinfo=UTC)
TEN_MINUTES_AGO = datetime(2026, 10, 19, 8, 50, tzinfo=UTC)
NEVER_STARTED = None


class IsOrderDueTest(unittest.TestCase):
    def test_should_find_due_an_active_order_whose_schedule_passed_since_its_last_run(self):
        # Arrange
        order = OrderFacts(name="nightly", every="30m", status="active", last_started=AN_HOUR_AGO, parked=False)

        # Act
        due = is_order_due(order, NOW)

        # Assert
        self.assertTrue(due)

    def test_should_find_due_an_active_order_on_a_schedule_never_run(self):
        # Arrange
        order = OrderFacts(name="nightly", every="30m", status="active", last_started=NEVER_STARTED, parked=False)

        # Act
        due = is_order_due(order, NOW)

        # Assert
        self.assertTrue(due)

    def test_should_not_find_due_an_order_whose_schedule_has_not_passed(self):
        # Arrange
        order = OrderFacts(name="nightly", every="30m", status="active", last_started=TEN_MINUTES_AGO, parked=False)

        # Act
        due = is_order_due(order, NOW)

        # Assert
        self.assertFalse(due)

    def test_should_never_find_due_an_order_on_demand(self):
        # Arrange
        on_demand = None
        order = OrderFacts(name="nightly", every=on_demand, status="active", last_started=NEVER_STARTED, parked=False)

        # Act
        due = is_order_due(order, NOW)

        # Assert
        self.assertFalse(due)

    def test_should_never_find_due_a_paused_order(self):
        # Arrange
        order = OrderFacts(name="nightly", every="30m", status="paused", last_started=AN_HOUR_AGO, parked=False)

        # Act
        due = is_order_due(order, NOW)

        # Assert
        self.assertFalse(due)

    def test_should_never_find_due_an_archived_order(self):
        # Arrange
        order = OrderFacts(name="nightly", every="30m", status="archived", last_started=AN_HOUR_AGO, parked=False)

        # Act
        due = is_order_due(order, NOW)

        # Assert
        self.assertFalse(due)

    def test_should_never_find_due_a_parked_order(self):
        # Arrange
        order = OrderFacts(name="nightly", every="30m", status="active", last_started=AN_HOUR_AGO, parked=True)

        # Act
        due = is_order_due(order, NOW)

        # Assert
        self.assertFalse(due)

    def test_should_refuse_a_schedule_it_cannot_read_naming_the_order(self):
        # Arrange
        order = OrderFacts(name="nightly", every="weekly", status="active", last_started=AN_HOUR_AGO, parked=False)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            is_order_due(order, NOW)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "@ORDER.nightly: the schedule weekly is none of <n>m, <n>h, daily@HH:MM or <day>@HH:MM, day mon to sun",
        )
