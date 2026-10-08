import unittest

from brigade.ledger.undeclared_event import UndeclaredEvent


class UndeclaredEventTest(unittest.TestCase):
    def test_should_read_the_name_of_an_event_brigade_does_not_declare(self):
        # Act
        event = UndeclaredEvent.from_document({"event": "study.done", "study": "health"})

        # Assert
        self.assertEqual(event, UndeclaredEvent(name="study.done"))
