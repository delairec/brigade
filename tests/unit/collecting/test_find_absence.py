import unittest

from brigade.collecting.find_absence import find_absence
from brigade.corpus.read_entity import Entity, EntityField

PROJECT_WITHOUT_FORGE = Entity(name="oak", fields=(EntityField(name="FORGE", value="none"),))
PROJECT_ON_GITHUB = Entity(name="oak", fields=(EntityField(name="FORGE", value="github"),))


class FindAbsenceTest(unittest.TestCase):
    def test_should_name_the_missing_forge_of_a_forge_collector(self):
        for name in ["pr-list", "check-runs", "pr-threads"]:
            with self.subTest(name=name):
                # Act
                absence = find_absence(name, PROJECT_WITHOUT_FORGE)

                # Assert
                self.assertEqual(absence, "FORGE none")

    def test_should_find_nothing_missing_for_a_project_with_a_forge_or_a_collector_needing_none(self):
        for name, project in [("pr-list", PROJECT_ON_GITHUB), ("git-log", PROJECT_WITHOUT_FORGE)]:
            with self.subTest(name=name, project=project):
                # Act
                absence = find_absence(name, project)

                # Assert
                self.assertIsNone(absence)
