import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.ledger import collect
from brigade.ledger.append_event import append_event
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.task_state import TaskState
from brigade.ledger.wave_started import WaveStarted
from brigade.system.parse_configuration import Configuration
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

EQUIPMENT = CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github")
ENVIRONMENT = {"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "2026-10-01", "BRIGADE_PARAMS": "{}"}
FINISHED_RUN = RunFinished(
    run="20261003T100000Z-aaaaaa",
    segment=1,
    procedure="awawa-task",
    slot="build",
    role="ada",
    client="claude-code",
    project="oak",
    session=None,
    main_steps=None,
    total_steps=None,
    duration_ms=None,
    usage=None,
    outcome="done",
    error_class=None,
    exit=0,
    wave=None,
    task=None,
    nulls={},
)


class LedgerCollectorTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(Path(directory.name), self.processes)
        paths = self.runtime.paths
        append_event(
            paths,
            datetime(2026, 9, 30, 23, 0, tzinfo=UTC),
            OrderStarted(project="oak", kind="study", order="trees", run="r0"),
        )
        append_event(
            paths,
            datetime(2026, 10, 2, 8, 0, tzinfo=UTC),
            OrderStarted(project="oak", kind="study", order="trees", run="r1"),
        )
        append_event(
            paths,
            datetime(2026, 10, 2, 9, 0, tzinfo=UTC),
            OrderDone(project="oak", kind="study", order="trees", run="r1"),
        )
        append_event(
            paths,
            datetime(2026, 10, 3, 8, 0, tzinfo=UTC),
            OrderStarted(project="elm", kind="study", order="ash", run="r2"),
        )
        append_event(paths, datetime(2026, 10, 3, 10, 0, tzinfo=UTC), FINISHED_RUN)

    def test_should_count_the_events_of_the_project_since_the_start(self):
        # Arrange
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})

        # Act
        document = collect(ENVIRONMENT, self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "ledger",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": True,
                "summary": {
                    "events": {"order.started": 1, "order.done": 1, "run.finished": 1},
                    "outcomes": {"done": 1},
                },
                "items": [
                    {
                        "ts": "2026-10-02T08:00:00Z",
                        "event": "order.started",
                        "project": "oak",
                        "kind": "study",
                        "order": "trees",
                        "run": "r1",
                    },
                    {
                        "ts": "2026-10-02T09:00:00Z",
                        "event": "order.done",
                        "project": "oak",
                        "kind": "study",
                        "order": "trees",
                        "run": "r1",
                    },
                    {
                        "ts": "2026-10-03T10:00:00Z",
                        "event": "run.finished",
                        "run": "20261003T100000Z-aaaaaa",
                        "segment": 1,
                        "procedure": "awawa-task",
                        "slot": "build",
                        "role": "ada",
                        "client": "claude-code",
                        "project": "oak",
                        "session": None,
                        "main_steps": None,
                        "total_steps": None,
                        "duration_ms": None,
                        "usage": None,
                        "outcome": "done",
                        "error_class": None,
                        "exit": 0,
                        "wave": None,
                        "task": None,
                        "nulls": {},
                    },
                ],
            },
        )

    def test_should_count_the_events_of_every_project_from_a_directory_no_project_is_registered_at(self):
        # Arrange
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {})

        # Act
        document = collect(ENVIRONMENT, self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(document["summary"]["events"], {"order.started": 2, "order.done": 1, "run.finished": 1})

    def test_should_keep_the_events_of_the_wave_it_names_whatever_their_project(self):
        # Arrange
        paths = self.runtime.paths
        append_event(
            paths,
            datetime(2026, 10, 4, 8, 0, tzinfo=UTC),
            WaveStarted(wave="oak_w2", project="oak", branch="integration/oak_w2", tasks=("B17",)),
        )
        append_event(
            paths, datetime(2026, 10, 4, 9, 0, tzinfo=UTC), TaskState(wave="oak_w2", task="B17", state="merged")
        )
        append_event(
            paths, datetime(2026, 10, 4, 9, 30, tzinfo=UTC), TaskState(wave="oak_w1", task="B16", state="merged")
        )
        wave_environment = {**ENVIRONMENT, "BRIGADE_PARAMS": '{"wave": "oak_w2"}'}

        # Act
        document = collect(wave_environment, self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(
            document["items"],
            [
                {
                    "ts": "2026-10-04T08:00:00Z",
                    "event": "wave.started",
                    "wave": "oak_w2",
                    "project": "oak",
                    "branch": "integration/oak_w2",
                    "tasks": ["B17"],
                },
                {
                    "ts": "2026-10-04T09:00:00Z",
                    "event": "task.state",
                    "wave": "oak_w2",
                    "task": "B17",
                    "state": "merged",
                },
            ],
        )

    def test_should_list_an_event_brigade_never_writes_with_what_it_carries(self):
        for line, expected_item in [
            (
                '{"schema_version": 1, "ts": "2026-10-04T08:00:00Z", "event": "constraint.delivered", "project": "oak"}',
                {"ts": "2026-10-04T08:00:00Z", "event": "constraint.delivered", "project": "oak"},
            ),
            (
                '{"schema_version": 1, "ts": "2026-10-04T08:00:00Z", "event": "pattern.ratified", "project": "oak"}',
                {"ts": "2026-10-04T08:00:00Z", "event": "pattern.ratified", "project": "oak"},
            ),
            (
                '{"schema_version": 1, "ts": "2026-10-04T08:00:00Z", "event": "wave.drawn", "wave": "oak_w2"}',
                {"ts": "2026-10-04T08:00:00Z", "event": "wave.drawn"},
            ),
        ]:
            with self.subTest(line=line):
                # Arrange
                directory = tempfile.TemporaryDirectory()
                self.addCleanup(directory.cleanup)
                processes = ScriptedProcesses()
                runtime = create_scripted_runtime(Path(directory.name), processes)
                no_registered_project = {}
                processes.answer_entities(runtime.paths.config_root, "PROJECT", no_registered_project)
                ledger_directory = runtime.paths.state_root / "ledger"
                ledger_directory.mkdir(parents=True)
                (ledger_directory / "2026-10.jsonl").write_text(line + "\n", encoding="utf-8")

                # Act
                document = collect(ENVIRONMENT, runtime, EQUIPMENT)

                # Assert
                self.assertEqual(document["items"], [expected_item])
