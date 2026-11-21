import unittest

from brigade.captures.replace_captures_section import replace_captures_section

NEW_SECTION = "## Captures\n\nat 4567def\n"


class ReplaceCapturesSectionTest(unittest.TestCase):
    def test_should_put_the_captures_of_the_new_head_in_place_of_those_of_the_old_one(self):
        # Arrange
        body = "Title\n\n## Captures\n\nat 0123abc\n\n## Checks\n\nok\n"

        # Act
        replaced = replace_captures_section(body, NEW_SECTION)

        # Assert
        self.assertEqual(replaced, "Title\n\n## Captures\n\nat 4567def\n\n## Checks\n\nok\n")

    def test_should_replace_a_section_closing_the_body(self):
        # Arrange
        body = "Title\n\n## Captures\n\nat 0123abc\n"

        # Act
        replaced = replace_captures_section(body, NEW_SECTION)

        # Assert
        self.assertEqual(replaced, "Title\n\n## Captures\n\nat 4567def\n")

    def test_should_add_the_section_to_a_body_holding_none(self):
        # Arrange
        body = "Title\n"

        # Act
        replaced = replace_captures_section(body, NEW_SECTION)

        # Assert
        self.assertEqual(replaced, "Title\n\n## Captures\n\nat 4567def\n")
