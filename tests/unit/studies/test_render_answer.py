import unittest

from brigade.studies.convert_study import Study
from brigade.studies.render_answer import name_answer, render_answer

STUDY = Study(
    name="trees",
    project=None,
    question=None,
    collectors=(),
    slot="none",
    every=None,
    output="entity:FINDING",
    answer_type="FINDING",
    status="active",
)


class NameAnswerTest(unittest.TestCase):
    def test_should_name_the_answer_after_its_study_and_run(self):
        # Act
        name = name_answer(STUDY, "20261019T090000Z-aaaaaa")

        # Assert
        self.assertEqual(name, "trees_20261019T090000Z_aaaaaa")


class RenderAnswerTest(unittest.TestCase):
    def test_should_fill_the_study_the_run_and_each_collected_document(self):
        # Arrange
        collected = [{"collector": "weather", "summary": {"days": 1}, "document": "/srv/document.json"}]

        # Act
        answer = render_answer(STUDY, "20261019T090000Z-aaaaaa", collected)

        # Assert
        self.assertEqual(
            answer,
            "FINDING trees_20261019T090000Z_aaaaaa\n"
            '\tSTUDY "trees"\n'
            '\tRUN "20261019T090000Z-aaaaaa"\n'
            '\tCOLLECTED "weather"\n'
            '\t\tSUMMARY "{\\"days\\": 1}"\n'
            '\t\tDOCUMENT "/srv/document.json"\n',
        )
