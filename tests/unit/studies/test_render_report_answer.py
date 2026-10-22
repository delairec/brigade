import json
import tempfile
import unittest
from pathlib import Path

from brigade.studies.convert_study import Study
from brigade.studies.render_report_answer import render_report_answer
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

RUN_ID = "20261022T150000Z-aaaaaa"
STUDY = Study(
    name="wave-report",
    project="oak",
    question=None,
    collectors=(),
    slot="report",
    every=None,
    output="entity:REPORT",
    answer_type="REPORT",
    status="active",
    wave="oak_w2",
)
LEDGER_ITEMS = [
    {"ts": "2026-10-04T08:00:00Z", "event": "wave.started", "wave": "oak_w2", "tasks": ["B17"]},
    {"ts": "2026-10-04T10:30:00Z", "event": "task.state", "wave": "oak_w2", "task": "B17", "state": "merged"},
]
PULL_REQUEST_ITEMS = [{"number": 178, "head": "task/oak_w2/B17", "state": "merged", "task": "B17"}]
TASK_ITEMS = [{"type": "TASK", "name": "B17", "fields": [{"name": "SPEC", "atoms": ['"the tick merges"']}]}]
CHANGE_ITEMS = [
    {"path": "corpus/tasks.awawa", "insertions": 3, "deletions": 1},
    {"path": "brigade/tick/plan.py", "insertions": 10, "deletions": 0},
]


class RenderReportAnswerTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes)

    def write_document(self, collector: str, items: list) -> dict:
        path = self.root / f"{collector}.json"
        path.write_text(json.dumps({"collector": collector, "items": items}), encoding="utf-8")
        return {"collector": collector, "summary": {}, "document": str(path)}

    def test_should_report_the_wave_from_the_documents_of_its_collectors(self):
        # Arrange
        self.processes.answer_entities(
            self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("CORPUS", "corpus"))}
        )
        collected = [
            self.write_document("ledger", LEDGER_ITEMS),
            self.write_document("pr-list", PULL_REQUEST_ITEMS),
            self.write_document("corpus", TASK_ITEMS),
            self.write_document("git-diff-stat", CHANGE_ITEMS),
        ]

        # Act
        answer = render_report_answer(self.runtime, STUDY, RUN_ID, collected)

        # Assert
        self.assertEqual(
            answer,
            "REPORT oak_w2\n"
            '\tWAVE "oak_w2"\n'
            '\tPROJECT "oak"\n'
            '\tTASK_ROW "B17 merged #178"\n'
            '\tSTATISTIC "tasks 1"\n'
            '\tSTATISTIC "merged 1"\n'
            '\tSTATISTIC "parked 0"\n'
            '\tSTATISTIC "runs 0"\n'
            '\tSTATISTIC "files 2"\n'
            '\tSTATISTIC "insertions 13"\n'
            '\tSTATISTIC "deletions 1"\n'
            '\tMANUAL_TEST "B17: the tick merges"\n'
            '\tINSTRUCTIONS_CHANGE "corpus/tasks.awawa +3 -1"\n',
        )
