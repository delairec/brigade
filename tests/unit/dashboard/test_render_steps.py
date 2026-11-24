import unittest

from brigade.dashboard.render_steps import render_steps


class RenderStepsTest(unittest.TestCase):
    def test_should_number_each_step_in_the_order_given(self):
        # Arrange
        steps = ("Run <code>brigade run note</code>.", "Read the brief.")

        # Act
        rendered = render_steps(steps)

        # Assert
        self.assertEqual(
            rendered,
            '<ol class="steps"><li><p>Run <code>brigade run note</code>.</p></li><li><p>Read the brief.</p></li></ol>',
        )
