import unittest

from brigade.dashboard.render_project_selector import render_project_selector

PROJECTS = {"schema_version": 1, "projects": [{"name": "oak"}, {"name": "<elm>"}]}


class RenderProjectSelectorTest(unittest.TestCase):
    def test_should_offer_all_projects_with_their_count_then_each_one_escaped_and_no_button(self):
        # Arrange
        no_project_chosen = None

        # Act
        rendered = render_project_selector(PROJECTS, no_project_chosen)

        # Assert
        self.assertEqual(
            rendered,
            '<label for="project">Project</label><select id="project" name="project">'
            '<option value="">All projects (2)</option>'
            '<option value="oak">oak</option><option value="&lt;elm&gt;">&lt;elm&gt;</option></select>',
        )

    def test_should_select_the_project_carried_in_the_address(self):
        # Act
        rendered = render_project_selector(PROJECTS, "oak")

        # Assert
        self.assertEqual(
            rendered,
            '<label for="project">Project</label><select id="project" name="project">'
            '<option value="">All projects (2)</option>'
            '<option value="oak" selected>oak</option><option value="&lt;elm&gt;">&lt;elm&gt;</option></select>',
        )
