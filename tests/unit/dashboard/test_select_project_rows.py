import unittest

from brigade.dashboard.select_project_rows import select_project_rows

WAVES = {
    "schema_version": 1,
    "waves": [{"wave": "w1", "project": "oak"}, {"wave": "w2", "project": "elm"}],
    "unit_files": ["/a.timer"],
}


class SelectProjectRowsTest(unittest.TestCase):
    def test_should_keep_every_row_when_no_project_is_chosen(self):
        # Arrange
        all_projects = None

        # Act
        selected = select_project_rows(WAVES, all_projects)

        # Assert
        self.assertEqual(
            selected,
            {
                "schema_version": 1,
                "waves": [{"wave": "w1", "project": "oak"}, {"wave": "w2", "project": "elm"}],
                "unit_files": ["/a.timer"],
            },
        )

    def test_should_keep_the_rows_of_the_chosen_project_and_those_naming_none(self):
        # Act
        selected = select_project_rows(WAVES, "oak")

        # Assert
        self.assertEqual(
            selected, {"schema_version": 1, "waves": [{"wave": "w1", "project": "oak"}], "unit_files": ["/a.timer"]}
        )
