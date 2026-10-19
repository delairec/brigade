import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.studies.collect_evidence import collect_evidence
from brigade.studies.convert_study import Study
from brigade.studies.study_run_context import StudyEquipment, StudyRunContext
from brigade.system.read_configuration import Configuration
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

RUN_ID = "20261019T090000Z-aaaaaa"
DOCUMENT = {
    "schema_version": 1,
    "collector": "weather",
    "collected_at": "2026-10-19T09:00:00Z",
    "summary": {"days": 1},
    "items": ["sun"],
}


class CollectorDouble:
    name = "weather"
    command = "brigade-collector-weather"

    def __init__(self):
        self.environments = []

    def collect(self, environment: dict, runtime, equipment) -> SimpleNamespace:
        self.environments.append(environment)
        return SimpleNamespace(exit_code=0, stdout=json.dumps(DOCUMENT), stderr="", duration_ms=40)


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


def refuse_forge(name: str):
    raise AssertionError(f"the collection resolved the forge {name}")


def refuse_launch(request, runtime):
    raise AssertionError("the collection launched a run")


class CollectEvidenceTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes)
        self.run_directory = self.root / "state" / "runs" / RUN_ID
        self.collector = CollectorDouble()
        self.resolved = []

    def resolve_collector(self, name: str, project: Path) -> CollectorDouble:
        self.resolved.append((name, project))
        return self.collector

    def create_context(self, project: str | None) -> StudyRunContext:
        equipment = StudyEquipment(
            collector_equipment=CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github"),
            resolve_collector=self.resolve_collector,
            document=None,
            resolve_forge=refuse_forge,
            launch_run=refuse_launch,
        )
        return StudyRunContext(
            runtime=self.runtime,
            study=create_study(project),
            run_id=RUN_ID,
            run_directory=self.run_directory,
            equipment=equipment,
        )

    def test_should_keep_the_document_of_each_collector_in_the_run(self):
        # Arrange
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})

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

    def test_should_collect_in_the_project_of_the_study_since_the_beginning_with_its_parameters(self):
        # Arrange
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})

        # Act
        collect_evidence(self.create_context("oak"))

        # Assert
        self.assertEqual(
            (self.resolved, self.collector.environments),
            (
                [("weather", Path("/srv/oak"))],
                [
                    {
                        "BRIGADE_PROJECT_PATH": "/srv/oak",
                        "BRIGADE_SINCE": "1970-01-01",
                        "BRIGADE_PARAMS": '{"city": "Lyon"}',
                    }
                ],
            ),
        )

    def test_should_collect_in_the_current_directory_for_a_study_of_no_project(self):
        # Act
        collect_evidence(self.create_context(None))

        # Assert
        self.assertEqual(self.resolved, [("weather", Path.cwd())])
