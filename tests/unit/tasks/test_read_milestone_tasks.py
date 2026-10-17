import json
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.tasks.read_milestone_tasks import read_milestone_tasks

PROJECT_TREE = Path("/srv/trees/brigade")
STATUS_OF_THE_F0_TASKS = (
    "awawa",
    "status",
    "TASK",
    "--where",
    "MILESTONE==@MILESTONE.F0",
    "--json",
    "/srv/trees/brigade",
)
SHOW_OF_B1 = ("awawa", "show", "@TASK.B1", "--json", "/srv/trees/brigade")
ANSWERS = {
    STATUS_OF_THE_F0_TASKS: {"entities": [{"type": "TASK", "name": "B1"}]},
    SHOW_OF_B1: {"fields": [{"name": "MILESTONE", "atoms": ["@MILESTONE.F0"]}]},
}


def answer_as_awawa(request: ProcessRequest) -> ProcessRecord:
    stdout = json.dumps(ANSWERS.get(request.argv, {"entities": []}))
    return ProcessRecord(argv=request.argv, cwd=request.cwd, exit_code=0, stdout=stdout, stderr="", duration_ms=1)


class ReadMilestoneTasksTest(unittest.TestCase):
    def test_should_read_the_tasks_the_milestone_gathers(self):
        # Act
        tasks = read_milestone_tasks(answer_as_awawa, PROJECT_TREE, "F0")

        # Assert
        self.assertEqual(tasks, (Entity(name="B1", fields=(EntityField(name="MILESTONE", value="@MILESTONE.F0"),)),))
