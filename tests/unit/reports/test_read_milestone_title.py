import unittest

from brigade.corpus.read_entities import Entity, EntityField
from brigade.reports.read_milestone_title import read_milestone_title
from tests.unit.commands.command_runtime import create_corpus_double

PROJECT_IN_AREA = Entity(
    name="brigade",
    fields=(EntityField("PATH", "/projects/brigade"), EntityField("MODE", "area"), EntityField("CORPUS", "corpus")),
)
PROJECT_IN_MODE_NONE = Entity(
    name="brigade", fields=(EntityField("PATH", "/projects/brigade"), EntityField("MODE", "none"))
)
NO_PROJECT_REGISTERED = ()
M13_REPORT = {
    "id": "brigade_M13",
    "kind": "milestone-report",
    "project": "brigade",
    "fields": [{"name": "MILESTONE", "value": "M13"}, {"name": "PROJECT", "value": "brigade"}],
}
M13_OF_THE_CORPUS = {"MILESTONE": {"M13": (("TITLE", "Run resumption"), ("STATUS", "reached"))}}
NO_MILESTONE_IN_THE_CORPUS = {}


def create_project_corpus_double(entities: dict):
    answer_from_the_corpus = create_corpus_double(entities)

    def answer(request):
        if request.cwd != "/projects/brigade/corpus":
            raise AssertionError(f"awawa ran in {request.cwd}")
        return answer_from_the_corpus(request)

    return answer


class ReadMilestoneTitleTest(unittest.TestCase):
    def test_should_read_the_title_of_the_milestone_in_the_corpus_of_its_project(self):
        # Arrange
        run_process = create_project_corpus_double(M13_OF_THE_CORPUS)

        # Act
        title = read_milestone_title(run_process, (PROJECT_IN_AREA,), M13_REPORT)

        # Assert
        self.assertEqual(title, "Run resumption")

    def test_should_give_no_title_when_the_corpus_of_the_project_lacks_the_milestone(self):
        # Arrange
        run_process = create_project_corpus_double(NO_MILESTONE_IN_THE_CORPUS)

        # Act
        title = read_milestone_title(run_process, (PROJECT_IN_AREA,), M13_REPORT)

        # Assert
        self.assertIsNone(title)

    def test_should_give_no_title_when_the_project_holds_no_corpus_or_is_not_registered(self):
        # Arrange
        run_process = create_project_corpus_double(M13_OF_THE_CORPUS)
        rows = [("in MODE none", (PROJECT_IN_MODE_NONE,)), ("not registered", NO_PROJECT_REGISTERED)]
        for case, projects in rows:
            with self.subTest(case=case):
                # Act
                title = read_milestone_title(run_process, projects, M13_REPORT)

                # Assert
                self.assertIsNone(title)

    def test_should_give_no_title_to_a_report_on_a_wave_or_a_task(self):
        # Arrange
        run_process = create_project_corpus_double(M13_OF_THE_CORPUS)
        rows = [
            {"id": "brigade_w57", "kind": "wave-report", "project": "brigade", "fields": []},
            {"id": "brigade_B231", "kind": "task-report", "project": "brigade", "fields": []},
        ]
        for report in rows:
            with self.subTest(report=report["id"]):
                # Act
                title = read_milestone_title(run_process, (PROJECT_IN_AREA,), report)

                # Assert
                self.assertIsNone(title)
