import unittest

from brigade.dashboard.render_step_line import StepLine, render_step_line


class RenderStepLineTest(unittest.TestCase):
    def test_should_step_from_each_value_to_the_next_under_its_ceiling(self):
        # Arrange
        line = StepLine(label="cap <B7>", state="soft_limit", values=(2, 4, 4, 1), ceiling=4)

        # Act
        rendered = render_step_line(line)

        # Assert
        self.assertEqual(
            rendered,
            '<svg class="step-line" viewBox="0 0 100 40" role="img" aria-label="cap &lt;B7&gt;">'
            '<path class="step-path tone-limit" d="M0 20 H25 V0 H50 V0 H75 V30 H100"></path></svg>',
        )

    def test_should_draw_no_line_without_values(self):
        # Arrange
        no_value = ()
        line = StepLine(label="cap", state="soft_limit", values=no_value, ceiling=4)

        # Act
        rendered = render_step_line(line)

        # Assert
        self.assertEqual(rendered, '<svg class="step-line" viewBox="0 0 100 40" role="img" aria-label="cap"></svg>')
