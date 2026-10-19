import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.study import collect
from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.order_done import OrderDone
from brigade.system.read_configuration import Configuration
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

EQUIPMENT = CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github")
STUDY_FIELDS = (("SLOT", "none"), ("OUTPUT", "entity:FINDING"), ("ANSWER", "FINDING"), ("STATUS", "active"))


def create_environment(parameters: str) -> dict:
    return {"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "2026-10-01", "BRIGADE_PARAMS": parameters}


class StudyCollectorTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes)

    def record_answer(self, run: str) -> None:
        append_event(
            self.runtime.paths,
            datetime(2026, 10, 2, 8, 0, tzinfo=UTC),
            OrderDone(project=None, kind="study", order="trees", run=run),
        )

    def test_should_collect_the_answer_of_the_last_run_of_the_study(self):
        # Arrange
        self.record_answer("20261001T080000Z-aaaaaa")
        self.record_answer("20261002T080000Z-bbbbbb")
        append_event(
            self.runtime.paths,
            datetime(2026, 10, 3, 8, 0, tzinfo=UTC),
            OrderDone(project=None, kind="study", order="ash", run="20261003T080000Z-cccccc"),
        )
        self.processes.answer_entity(self.runtime.paths.config_root, "STUDY", "trees", STUDY_FIELDS)
        answer = self.root / "state" / "runs" / "20261002T080000Z-bbbbbb" / "answer.awawa"
        self.processes.answer_json(
            ("awawa", "show", "@FINDING.trees_20261002T080000Z_bbbbbb", "--json", str(answer)),
            {"fields": [{"name": "VERDICT", "atoms": ['"two "', '"oaks"']}]},
        )

        # Act
        document = collect(create_environment('{"name": "trees"}'), self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "study",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": False,
                "summary": {"run": "20261002T080000Z-bbbbbb"},
                "items": [
                    {
                        "type": "FINDING",
                        "name": "trees_20261002T080000Z_bbbbbb",
                        "fields": [{"name": "VERDICT", "value": "two oaks"}],
                    }
                ],
            },
        )

    def test_should_refuse_a_study_that_has_no_answer_yet(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            collect(create_environment('{"name": "trees"}'), self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(str(refusal.exception), "@STUDY.trees has no answer yet")

    def test_should_refuse_to_collect_without_the_name_of_a_study(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            collect(create_environment("{}"), self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(str(refusal.exception), "the study collector takes name=<study>")
