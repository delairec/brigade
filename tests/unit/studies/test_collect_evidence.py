import json
import tempfile
import unittest
from pathlib import Path

from brigade.studies.collect_evidence import collect_evidence
from brigade.studies.convert_study import Study
from brigade.studies.study_run_context import StudyRunContext
from brigade.system.run_process import ProcessRecord
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.studies.create_study_equipment import create_study_equipment

RUN_ID = "20261019T090000Z-aaaaaa"
WORKING_DIRECTORY = Path("/srv/elm")
DOCUMENT = {
    "schema_version": 1,
    "collector": "weather",
    "collected_at": "2026-10-19T09:00:00Z",
    "summary": {"days": 1},
    "items": ["sun"],
}

COLLECTOR_DIRECTORY = "/srv/shop"


class CollectorDouble:
    name = "weather"
    command = "brigade-collector-weather"

    def __init__(self):
        self.environments = []

    def collect(self, environment: dict, runtime, equipment) -> ProcessRecord:
        self.environments.append(environment)
        return ProcessRecord(
            argv=(self.command,),
            cwd=COLLECTOR_DIRECTORY,
            exit_code=0,
            stdout=json.dumps(DOCUMENT),
            stderr="",
            duration_ms=40,
        )


def create_study(project: str | None) -> Study:
    return Study(
        name="trees",
        project=project,
        question=None,
        collectors=("weather city=Lyon",),
        slot="none",
        every=None,
        output="entity:FINDING",
        answer_type="FINDING",
        status="active",
    )


class CollectEvidenceTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
        self.run_directory = self.root / "state" / "runs" / RUN_ID
        self.collector = CollectorDouble()
        self.resolved = []

    def resolve_collector(self, name: str, project: Path) -> CollectorDouble:
        self.resolved.append((name, project))
        return self.collector

    def create_context(self, project: str | None) -> StudyRunContext:
        equipment = create_study_equipment(
            resolve_collector=self.resolve_collector, working_directory=WORKING_DIRECTORY
        )
        return StudyRunContext(
            runtime=self.runtime,
            study=create_study(project),
            run_id=RUN_ID,
            run_directory=self.run_directory,
            equipment=equipment,
        )

    def register_project(self) -> None:
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})

    def test_should_keep_the_document_of_each_collector_in_the_run(self):
        # Arrange
        self.register_project()

        # Act
        collected = collect_evidence(self.create_context("oak"))

        # Assert
        self.assertEqual(
            collected,
            {
                "collected": [
                    {
                        "collector": "weather",
                        "summary": {"days": 1},
                        "document": str(
                            self.run_directory / "collectors" / "1" / "collect" / "weather" / "document.json"
                        ),
                    }
                ]
            },
        )

    def test_should_resolve_each_collector_for_the_project_of_the_study(self):
        # Arrange
        self.register_project()

        # Act
        collect_evidence(self.create_context("oak"))

        # Assert
        self.assertEqual(self.resolved, [("weather", Path("/srv/oak"))])

    def test_should_collect_since_the_beginning_with_the_parameters_of_the_collector_line(self):
        # Arrange
        self.register_project()

        # Act
        collect_evidence(self.create_context("oak"))

        # Assert
        self.assertEqual(
            self.collector.environments,
            [{"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "1970-01-01", "BRIGADE_PARAMS": '{"city": "Lyon"}'}],
        )

    def test_should_collect_in_the_working_directory_of_brigade_for_a_study_of_no_project(self):
        # Act
        collect_evidence(self.create_context(None))

        # Assert
        self.assertEqual(self.resolved, [("weather", Path("/srv/elm"))])
