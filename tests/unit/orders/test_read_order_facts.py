import unittest
from datetime import UTC, datetime

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.orders.convert_order import Order
from brigade.orders.is_order_due import OrderFacts
from brigade.orders.read_order_facts import read_order_facts

NIGHTLY = Order(
    name="nightly",
    recipe="usage-report",
    project="shop",
    text=None,
    params=(),
    every="24h",
    output=None,
    status="active",
)
FIRST_START = datetime(2026, 10, 18, 9, 0, tzinfo=UTC)
SECOND_START = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)
LATER = datetime(2026, 10, 19, 9, 20, tzinfo=UTC)
NO_EVENT = ()


class ReadOrderFactsTest(unittest.TestCase):
    def test_should_read_an_order_never_run_as_never_started_and_not_parked(self):
        # Act
        facts = read_order_facts((NIGHTLY,), NO_EVENT)

        # Assert
        self.assertEqual(
            facts,
            (OrderFacts(name="nightly", every="24h", status="active", last_started=None, parked=False),),
        )

    def test_should_read_the_last_start_of_an_order_and_its_park_by_its_last_run(self):
        # Arrange
        entries = (
            LedgerEntry(FIRST_START, OrderStarted(project="shop", kind="usage-report", order="nightly", run="r1")),
            LedgerEntry(FIRST_START, OrderDone(project="shop", kind="usage-report", order="nightly", run="r1")),
            LedgerEntry(SECOND_START, OrderStarted(project="shop", kind="usage-report", order="nightly", run="r2")),
            LedgerEntry(
                LATER,
                OrderParked(
                    project="shop", kind="usage-report", order="nightly", run="r2", step="1-gate", reason="red"
                ),
            ),
        )

        # Act
        facts = read_order_facts((NIGHTLY,), entries)

        # Assert
        self.assertEqual(
            facts,
            (OrderFacts(name="nightly", every="24h", status="active", last_started=SECOND_START, parked=True),),
        )

    def test_should_read_an_order_whose_parked_run_was_resumed_as_not_parked(self):
        # Arrange
        entries = (
            LedgerEntry(FIRST_START, OrderStarted(project="shop", kind="usage-report", order="nightly", run="r1")),
            LedgerEntry(
                FIRST_START,
                OrderParked(
                    project="shop", kind="usage-report", order="nightly", run="r1", step="1-gate", reason="red"
                ),
            ),
            LedgerEntry(LATER, OrderDone(project="shop", kind="usage-report", order="nightly", run="r1")),
        )

        # Act
        facts = read_order_facts((NIGHTLY,), entries)

        # Assert
        self.assertEqual(
            facts,
            (OrderFacts(name="nightly", every="24h", status="active", last_started=FIRST_START, parked=False),),
        )

    def test_should_ignore_the_events_of_a_study_of_the_same_name(self):
        # Arrange
        entries = (
            LedgerEntry(FIRST_START, OrderStarted(project=None, kind="study", order="nightly", run="r1")),
            LedgerEntry(
                LATER,
                OrderParked(project=None, kind="study", order="nightly", run="r1", step="judge", reason="red"),
            ),
        )

        # Act
        facts = read_order_facts((NIGHTLY,), entries)

        # Assert
        self.assertEqual(
            facts,
            (OrderFacts(name="nightly", every="24h", status="active", last_started=None, parked=False),),
        )
