import unittest

from brigade.dashboard.render_project_selector import render_project_selector

PROJECTS = {"schema_version": 1, "projects": [{"name": "oak"}, {"name": "<elm>"}]}


class RenderProjectSelectorTest(unittest.TestCase):
    def test_should_offer_all_projects_then_each_one_escaped(self):
        # Arrange
        no_project_chosen = None

        # Act
        rendered = render_project_selector(PROJECTS, no_project_chosen)

        # Assert
        self.assertEqual(
            rendered,
            '<label>Project <select name="project"><option value="">All projects</option>'
            '<option value="oak">oak</option><option value="&lt;elm&gt;">&lt;elm&gt;</option></select></label>'
            "<button>show</button>",
        )

    def test_should_select_the_project_carried_in_the_address(self):
        # Act
        rendered = render_project_selector(PROJECTS, "oak")

        # Assert
        self.assertEqual(
            rendered,
            '<label>Project <select name="project"><option value="">All projects</option>'
            '<option value="oak" selected>oak</option><option value="&lt;elm&gt;">&lt;elm&gt;</option></select>'
            "</label><button>show</button>",
        )
