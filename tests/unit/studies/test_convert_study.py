import unittest

from brigade.corpus.read_entity import Entity, EntityField
from brigade.studies.convert_study import Study, convert_study


class ConvertStudyTest(unittest.TestCase):
    def test_should_convert_a_study_of_a_project_asking_a_question_on_a_schedule(self):
        # Arrange
        entity = Entity(
            name="trees",
            fields=(
                EntityField(name="PROJECT", value="@PROJECT.oak"),
                EntityField(name="QUESTION", value="how many trees?"),
                EntityField(name="COLLECTOR", value="git-log"),
                EntityField(name="COLLECTOR", value="ledger"),
                EntityField(name="SLOT", value="review"),
                EntityField(name="EVERY", value="daily@07:00"),
                EntityField(name="OUTPUT", value="issue"),
                EntityField(name="ANSWER", value="FINDING"),
                EntityField(name="STATUS", value="active"),
            ),
        )

        # Act
        study = convert_study(entity)

        # Assert
        self.assertEqual(
            study,
            Study(
                name="trees",
                project="oak",
                question="how many trees?",
                collectors=("git-log", "ledger"),
                slot="review",
                every="daily@07:00",
                output="issue",
                answer_type="FINDING",
                status="active",
            ),
        )

    def test_should_convert_a_scan_of_no_project_run_on_demand(self):
        # Arrange
        entity = Entity(
            name="scan",
            fields=(
                EntityField(name="SLOT", value="none"),
                EntityField(name="OUTPUT", value="entity:FINDING"),
                EntityField(name="ANSWER", value="FINDING"),
                EntityField(name="STATUS", value="paused"),
            ),
        )

        # Act
        study = convert_study(entity)

        # Assert
        self.assertEqual(
            study,
            Study(
                name="scan",
                project=None,
                question=None,
                collectors=(),
                slot="none",
                every=None,
                output="entity:FINDING",
                answer_type="FINDING",
                status="paused",
            ),
        )
