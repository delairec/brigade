import unittest

from brigade.dashboard.read_state_tone import read_state_tone


class ReadStateToneTest(unittest.TestCase):
    def test_should_give_each_state_the_tone_of_what_it_asks(self):
        # Arrange
        rows = [
            ("parked", "you"),
            ("blocked", "you"),
            ("paused", "you"),
            ("running", "work"),
            ("fixing", "work"),
            ("pr_open", "review"),
            ("verifying", "review"),
            ("changes_requested", "review"),
            ("merged", "done"),
            ("verified", "done"),
            ("done", "done"),
            ("closed", "done"),
            ("reached", "done"),
            ("blocked:quota", "limit"),
            ("wall_limit", "limit"),
            ("turn_limit", "limit"),
            ("soft_limit", "limit"),
            ("dead", "failed"),
            ("failed", "failed"),
            ("cancelled", "off"),
            ("stopped", "off"),
            ("dismissed", "off"),
            ("queued", "faint"),
            ("handed_over", "faint"),
        ]
        for state, tone in rows:
            with self.subTest(state=state):
                # Act
                read = read_state_tone(state)

                # Assert
                self.assertEqual(read, tone)

    def test_should_leave_a_state_it_does_not_know_neutral(self):
        # Act
        tone = read_state_tone("<unknown>")

        # Assert
        self.assertEqual(tone, "faint")
