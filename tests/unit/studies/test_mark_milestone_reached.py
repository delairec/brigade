import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.studies.mark_milestone_reached import mark_milestone_reached
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

MESSAGE = "docs(corpus): mark @MILESTONE.M4 reached"
MILESTONES = "MILESTONE M4\n\tSTATUS active\n"


class MarkMilestoneReachedTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.checkout = self.root / "checkout"
        (self.checkout / "brigade").mkdir(parents=True)
        (self.checkout / "brigade" / "milestones.awawa").write_text(MILESTONES, encoding="utf-8")
        self.processes = ScriptedProcesses()

    def test_should_set_the_status_in_the_file_of_the_area_and_lint_the_area(self):
        # Arrange
        area = self.checkout / "brigade"
        project = Entity(
            name="oak",
            fields=(EntityField(name="CORPUS", value="brigade"), EntityField(name="MODE", value="area")),
        )
        self.processes.answer_json(
            ("awawa", "show", "@MILESTONE.M4", "--json", str(area)),
            {"file": str(area / "milestones.awawa"), "fields": []},
        )
        self.processes.answer_corpus_change(self.checkout, ("brigade/milestones.awawa",), MESSAGE)
        self.processes.answer(("awawa", "lint", "--strict", str(area)))
        runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)

        # Act
        mark_milestone_reached(runtime, self.checkout, project, "M4")

        # Assert
        self.assertIn("STATUS reached", (area / "milestones.awawa").read_text(encoding="utf-8"))
        self.assertIn(("awawa", "lint", "--strict", str(area)), self.processes.list_argvs())
