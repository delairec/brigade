import unittest

from brigade.dashboard.render_next_tick import render_next_tick

NOTHING_DECIDED = {"schema_version": 1, "mode": "dry-run", "snapshot": {}, "decisions": []}


class RenderNextTickTest(unittest.TestCase):
    def test_should_group_the_decisions_of_the_next_tick_by_their_action(self):
        # Arrange
        document = {
            **NOTHING_DECIDED,
            "decisions": [
                {"action": "LaunchTask", "project": "oak", "wave": "oak_w2", "task": "B2"},
                {"action": "CollectCheckRuns", "project": "oak"},
                {"action": "LaunchTask", "project": "oak", "wave": "oak_w2", "task": "B3"},
            ],
        }

        # Act
        fragment = render_next_tick(document)

        # Assert
        self.assertEqual(
            fragment,
            "<h3>LaunchTask</h3><ul><li>project oak, wave oak_w2, task B2</li>"
            "<li>project oak, wave oak_w2, task B3</li></ul>"
            "<h3>CollectCheckRuns</h3><ul><li>project oak</li></ul>",
        )

    def test_should_say_the_next_tick_decides_nothing(self):
        # Act
        fragment = render_next_tick(NOTHING_DECIDED)

        # Assert
        self.assertEqual(fragment, '<p class="next-tick-empty">the next tick decides nothing</p>')

    def test_should_escape_a_decision_holding_markup(self):
        # Arrange
        document = {**NOTHING_DECIDED, "decisions": [{"action": "<b>Act</b>", "wave": "<i>w</i>"}]}

        # Act
        fragment = render_next_tick(document)

        # Assert
        self.assertEqual(fragment, "<h3>&lt;b&gt;Act&lt;/b&gt;</h3><ul><li>wave &lt;i&gt;w&lt;/i&gt;</li></ul>")
