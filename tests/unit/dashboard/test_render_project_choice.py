import unittest

from brigade.dashboard.render_project_choice import render_project_choice

MARKUP = '"><script>alert(1)</script>'


class RenderProjectChoiceTest(unittest.TestCase):
    def test_should_offer_every_registered_project_in_the_selector(self):
        # Arrange
        projects = {
            "schema_version": 1,
            "projects": [{"name": "oak", "path": "/srv/oak"}, {"name": "elm", "path": "/srv/elm"}],
        }

        # Act
        fragment = render_project_choice(projects)

        # Assert
        self.assertEqual(
            fragment,
            '<form class="corpus-selector" method="get">'
            '<label>project <select name="project">'
            '<option value="oak">oak</option><option value="elm">elm</option></select></label>'
            '<label>ref <input name="ref" value=""></label>'
            '<label>type <input name="type" list="corpus-types" value=""></label>'
            '<datalist id="corpus-types"></datalist>'
            '<label>board field <input name="field" value=""></label>'
            "<button>read</button></form>",
        )

    def test_should_escape_the_name_of_a_project(self):
        # Arrange
        projects = {"schema_version": 1, "projects": [{"name": MARKUP, "path": "/srv/oak"}]}

        # Act
        fragment = render_project_choice(projects)

        # Assert
        self.assertNotIn("<script>", fragment)
