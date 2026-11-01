import unittest

from brigade.dashboard.render_project_choice import render_project_choice

MARKUP = '"><script>alert(1)</script>'


class RenderProjectChoiceTest(unittest.TestCase):
    def test_should_link_every_registered_project_to_its_corpus_view(self):
        # Arrange
        projects = {
            "schema_version": 1,
            "projects": [{"name": "oak", "path": "/srv/oak"}, {"name": "elm", "path": "/srv/elm"}],
        }

        # Act
        fragment = render_project_choice(projects)

        # Assert
        self.assertEqual(
            fragment, '<ul><li><a href="#corpus/oak">oak</a></li><li><a href="#corpus/elm">elm</a></li></ul>'
        )

    def test_should_escape_the_name_of_a_project(self):
        # Arrange
        projects = {"schema_version": 1, "projects": [{"name": MARKUP, "path": "/srv/oak"}]}

        # Act
        fragment = render_project_choice(projects)

        # Assert
        self.assertNotIn("<script>", fragment)
