import unittest
from pathlib import Path

from brigade.registry.derive_project_name import derive_project_name


class DeriveProjectName(unittest.TestCase):
    def test_should_turn_the_basename_into_an_identifier(self):
        rows = [
            ("/srv/brigade", "brigade"),
            ("/srv/my-app.v2", "my_app_v2"),
            ("/srv/Planet Crafter", "Planet_Crafter"),
            ("/srv/2048", "2048"),
            ("/srv/café", "caf_"),
        ]
        for path, expected in rows:
            with self.subTest(path=path):
                # Act
                name = derive_project_name(Path(path))

                # Assert
                self.assertEqual(name, expected)
