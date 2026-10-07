import unittest

from brigade.system.render_table import render_table


class RenderTableTest(unittest.TestCase):
    def test_should_align_every_column_on_its_widest_cell_the_header_included(self):
        # Arrange
        header = ("name", "status", "path")
        rows = [("alpha", "active", "/srv/alpha"), ("the_beta", "paused", "/srv/beta")]

        # Act
        text = render_table(header, rows)

        # Assert
        self.assertEqual(
            text.splitlines(),
            [
                "name      status  path",
                "alpha     active  /srv/alpha",
                "the_beta  paused  /srv/beta",
            ],
        )

    def test_should_leave_the_last_column_unpadded(self):
        # Arrange
        header = ("slot", "model")
        rows = [("plan", "fable"), ("rebase", "-")]

        # Act
        text = render_table(header, rows)

        # Assert
        self.assertEqual(text, "slot    model\nplan    fable\nrebase  -")
