import unittest

from brigade.commands.render_roles_lint_text import render_roles_lint_text


class RenderRolesLintTextTest(unittest.TestCase):
    def test_should_summarise_when_there_are_no_findings(self):
        # Arrange
        document = {"files": ["a.md", "b.md"], "findings": []}

        # Act
        text = render_roles_lint_text(document)

        # Assert
        self.assertEqual(text, "roles lint: 2 files, 0 findings")

    def test_should_render_a_finding_without_a_key(self):
        # Arrange
        document = {
            "files": ["a.md"],
            "findings": [{"file": "a.md", "key": None, "problem": "unreadable"}],
        }

        # Act
        text = render_roles_lint_text(document)

        # Assert
        self.assertEqual(text, "a.md: unreadable\n\nroles lint: 1 files, 1 finding")

    def test_should_render_a_finding_with_a_key(self):
        # Arrange
        document = {
            "files": ["a.md"],
            "findings": [{"file": "a.md", "key": "slot", "problem": "duplicate"}],
        }

        # Act
        text = render_roles_lint_text(document)

        # Assert
        self.assertEqual(text, "a.md: slot duplicate\n\nroles lint: 1 files, 1 finding")

    def test_should_use_the_plural_when_there_are_several_findings(self):
        # Arrange
        document = {
            "files": ["a.md"],
            "findings": [
                {"file": "a.md", "key": None, "problem": "unreadable"},
                {"file": "a.md", "key": "slot", "problem": "duplicate"},
            ],
        }

        # Act
        text = render_roles_lint_text(document)

        # Assert
        self.assertEqual(text, "a.md: unreadable\na.md: slot duplicate\n\nroles lint: 1 files, 2 findings")
