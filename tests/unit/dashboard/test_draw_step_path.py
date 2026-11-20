import unittest

from brigade.dashboard.draw_step_path import StepFrame, StepPath, draw_step_path


class DrawStepPathTest(unittest.TestCase):
    def test_should_step_from_each_value_to_the_next_scaled_to_the_ceiling(self):
        # Arrange
        frame = StepFrame(width=100, top=0, height=40)

        # Act
        path = draw_step_path((2, 4, 1), 4, "limit", frame)

        # Assert
        self.assertEqual(
            path,
            StepPath(
                markup='<path class="step-path tone-limit" d="M0 20 H33.3333 V0 H66.6667 V30 H100"></path>',
                corners=((0, 20), (100 / 3, 0), (200 / 3, 30)),
            ),
        )

    def test_should_place_the_line_below_the_top_of_its_frame(self):
        # Arrange
        frame = StepFrame(width=400, top=20, height=40)

        # Act
        path = draw_step_path((60, 90), 90, "work", frame)

        # Assert
        self.assertEqual(path.markup, '<path class="step-path tone-work" d="M0 33.3333 H200 V20 H400"></path>')
        self.assertEqual(path.corners, ((0, 20 + 40 * (1 - 60 / 90)), (200, 20)))

    def test_should_draw_a_flat_line_for_a_single_value(self):
        # Arrange
        frame = StepFrame(width=400, top=20, height=40)

        # Act
        path = draw_step_path((40,), 40, "work", frame)

        # Assert
        self.assertEqual(
            path, StepPath(markup='<path class="step-path tone-work" d="M0 20 H400"></path>', corners=((0, 20),))
        )
