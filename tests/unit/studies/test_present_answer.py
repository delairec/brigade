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


def create_context(document: DocumentDouble) -> StudyRunContext:
    equipment = StudyEquipment(
        collector_equipment=None, resolve_collector=None, document=document, resolve_forge=None, launch_run=None
    )
    return StudyRunContext(
        runtime=None, study=STUDY, run_id="r1", run_directory=Path("/srv/runs/r1"), equipment=equipment
    )


class PresentAnswerTest(unittest.TestCase):
    def test_should_present_each_entity_of_the_answer_as_a_markdown_section(self):
        # Act
        publication = present_answer(create_context(DocumentDouble()))

        # Assert
        self.assertEqual(
            publication,
            AnswerPublication(
                title="Study trees, run r1",
                markdown="# FINDING trees_1\n\n- STUDY: trees\n- VERDICT: two oaks\n\n# FINDING trees_2\n\n",
            ),
        )

    def test_should_render_the_answer_file_of_the_run(self):
        # Arrange
        document = DocumentDouble()

        # Act
        present_answer(create_context(document))

        # Assert
        self.assertEqual(document.requests, [{"path": "/srv/runs/r1/answer.awawa"}])
