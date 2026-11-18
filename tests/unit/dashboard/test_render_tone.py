import unittest

from brigade.dashboard.render_tone import render_tone


class RenderToneTest(unittest.TestCase):
    def test_should_show_the_state_by_its_word_and_the_shape_of_its_tone(self):
        # Arrange
        rows = [
            ("parked", '<span class="tone tone-you"><span class="tone-shape" aria-hidden="true">▲</span>parked</span>'),
            (
                "running",
                '<span class="tone tone-work"><span class="tone-shape" aria-hidden="true">●</span>running</span>',
            ),
            (
                "pr_open",
                '<span class="tone tone-review"><span class="tone-shape" aria-hidden="true">◆</span>pr_open</span>',
            ),
            (
                "merged",
                '<span class="tone tone-done"><span class="tone-shape" aria-hidden="true">✓</span>merged</span>',
            ),
            (
                "wall_limit",
                '<span class="tone tone-limit"><span class="tone-shape" aria-hidden="true">■</span>wall_limit</span>',
            ),
            ("dead", '<span class="tone tone-failed"><span class="tone-shape" aria-hidden="true">✕</span>dead</span>'),
            (
                "cancelled",
                '<span class="tone tone-off"><span class="tone-shape" aria-hidden="true">○</span>cancelled</span>',
            ),
            (
                "queued",
                '<span class="tone tone-faint"><span class="tone-shape" aria-hidden="true">·</span>queued</span>',
            ),
        ]
        for state, expected in rows:
            with self.subTest(state=state):
                # Act
                tone = render_tone(state)

                # Assert
                self.assertEqual(tone, expected)

    def test_should_escape_a_state_holding_markup(self):
        # Act
        tone = render_tone("<b>parked</b>")

        # Assert
        self.assertEqual(
            tone,
            '<span class="tone tone-faint"><span class="tone-shape" aria-hidden="true">·</span>'
            "&lt;b&gt;parked&lt;/b&gt;</span>",
        )
