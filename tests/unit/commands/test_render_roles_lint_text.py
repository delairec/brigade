import unittest

from brigade.commands.render_roles_lint_text import render_roles_lint_text


class RenderRolesLintTextTest(unittest.TestCase):
    def test_should_name_the_file_alone_for_a_finding_on_no_key(self):
        # Arrange
        document = {
            "files": ["/srv/roles/planner.md"],
            "findings": [
                {"file": "/srv/roles/planner.md", "key": None, "problem": "has no front matter between two --- lines"}
            ],
        }

        # Act
        text = render_roles_lint_text(document)

        # Assert
        self.assertEqual(
            text,
            "/srv/roles/planner.md: has no front matter between two --- lines\n\nroles lint: 1 files, 1 finding",
        )

    def test_should_print_the_count_alone_when_nothing_is_found(self):
        # Arrange
        document = {"files": ["/srv/roles/planner.md", "/srv/roles/builder.md"], "findings": []}

        # Act
        text = render_roles_lint_text(document)

        # Assert
        self.assertEqual(text, "roles lint: 2 files, 0 findings")
