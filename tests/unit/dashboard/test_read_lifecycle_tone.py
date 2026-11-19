import unittest

from brigade.dashboard.read_lifecycle_tone import read_lifecycle_tone


class ReadLifecycleToneTest(unittest.TestCase):
    def test_should_give_each_status_of_a_corpus_the_tone_of_its_place_in_the_lifecycle(self):
        rows = [
            ("draft", "faint"),
            ("planned", "faint"),
            ("open", "you"),
            ("todo", "work"),
            ("active", "work"),
            ("implemented", "done"),
            ("reached", "done"),
            ("closed", "done"),
            ("archived", "off"),
            ("rejected", "off"),
            ("a status of the project's own", "faint"),
            (None, "faint"),
        ]
        for status, tone in rows:
            with self.subTest(status=status):
                # Act
                read = read_lifecycle_tone(status)

                # Assert
                self.assertEqual(read, tone)
