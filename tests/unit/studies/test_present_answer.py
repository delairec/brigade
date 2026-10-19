import unittest
from pathlib import Path

from brigade.studies.convert_study import Study
from brigade.studies.present_answer import AnswerPublication, present_answer
from brigade.studies.study_run_context import StudyEquipment, StudyRunContext

STUDY = Study(
    name="trees",
    project=None,
    question=None,
    collectors=(),
    slot="none",
    every=None,
    output="issue",
    answer_type="FINDING",
    status="active",
)
RENDERING = {
    "entities": [
        {
            "type": "FINDING",
            "name": "trees_1",
            "fields": [{"name": "STUDY", "value": "trees"}, {"name": "VERDICT", "value": "two oaks"}],
        },
        {"type": "FINDING", "name": "trees_2", "fields": []},
    ]
}


class DocumentDouble:
    def __init__(self):
        self.requests = []

    def render_document(self, request: dict, runtime) -> dict:
        self.requests.append(request)
        return RENDERING


class PresentAnswerTest(unittest.TestCase):
    def test_should_present_each_entity_of_the_answer_as_a_markdown_section(self):
        # Arrange
        document = DocumentDouble()
        equipment = StudyEquipment(
            collector_equipment=None, resolve_collector=None, document=document, resolve_forge=None, launch_run=None
        )
        context = StudyRunContext(
            runtime=None, study=STUDY, run_id="r1", run_directory=Path("/srv/runs/r1"), equipment=equipment
        )

        # Act
        publication = present_answer(context)

        # Assert
        self.assertEqual(
            (publication, document.requests),
            (
                AnswerPublication(
                    title="Study trees, run r1",
                    markdown="# FINDING trees_1\n\n- STUDY: trees\n- VERDICT: two oaks\n\n# FINDING trees_2\n\n",
                ),
                [{"path": "/srv/runs/r1/answer.awawa"}],
            ),
        )
