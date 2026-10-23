import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.collector_places import CollectorPlaces
from brigade.system.resolve_collector import BuiltInCollector, CollectorAnswer, ExecutableCollector, resolve_collector
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

NO_EQUIPMENT = None


def write_executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755)
    return path


class ResolveCollectorTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.places = CollectorPlaces(
            project_directory=self.root / "shop" / ".brigade" / "collectors",
            machine_directory=self.root / "config" / "collectors",
            executable_search_path=str(self.root / "bin"),
        )


class ResolveCollectorFoundTest(ResolveCollectorTestCase):
    def test_should_prefer_the_project_then_the_machine_then_path_then_the_built_ins(self):
        # Arrange
        write_executable(self.places.project_directory / "coverage")
        write_executable(self.places.machine_directory / "coverage")
        write_executable(self.places.machine_directory / "flakes")
        write_executable(self.root / "bin" / "brigade-collector-flakes")
        write_executable(self.root / "bin" / "brigade-collector-latency")

        for name, expected in [
            (
                "coverage",
                ExecutableCollector(
                    name="coverage", source="project", command=str(self.places.project_directory / "coverage")
                ),
            ),
            (
                "flakes",
                ExecutableCollector(
                    name="flakes", source="machine", command=str(self.places.machine_directory / "flakes")
                ),
            ),
            (
                "latency",
                ExecutableCollector(
                    name="latency", source="PATH", command=str(self.root / "bin" / "brigade-collector-latency")
                ),
            ),
        ]:
            with self.subTest(name=name):
                # Act
                collector = resolve_collector(name, self.places)

                # Assert
                self.assertEqual(collector, expected)

    def test_should_resolve_a_built_in_collector_by_its_dashed_name(self):
        # Act
        collector = resolve_collector("pr-list", self.places)

        # Assert
        self.assertEqual(collector.source, "built-in")
        self.assertEqual(collector.command, "brigade.collectors.pr_list")


class ResolveCollectorNotFoundTest(ResolveCollectorTestCase):
    def test_should_refuse_a_name_found_nowhere_or_off_the_pattern(self):
        for name in ["missing", "../coverage"]:
            with self.subTest(name=name):
                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    resolve_collector(name, self.places)

                # Assert
                self.assertEqual(
                    str(refusal.exception),
                    f"no collector {name} in {self.places.project_directory}, in {self.places.machine_directory},"
                    f" as brigade-collector-{name} on PATH or among the built-ins of brigade/collectors",
                )


class ExecutableCollectorTest(ResolveCollectorTestCase):
    def test_should_run_the_executable_in_the_project_and_answer_whatever_it_exits(self):
        # Arrange
        runner = RecordingProcessRunner(
            {("/opt/coverage",): ProcessAnswer(exit_code=3, stdout="{}", stderr="partial\n")}
        )
        runtime = create_test_runtime(create_test_paths(self.root), run_process=runner)
        collector = ExecutableCollector(name="coverage", source="machine", command="/opt/coverage")

        # Act
        answer = collector.collect({"BRIGADE_PROJECT_PATH": "/srv/shop"}, runtime, NO_EQUIPMENT)

        # Assert
        self.assertEqual(answer, CollectorAnswer(exit_code=3, stdout="{}", stderr="partial\n", duration_ms=0))
        self.assertEqual(runner.commands, [("/srv/shop", ("/opt/coverage",))])


class CollectingModuleDouble:
    def __init__(self, failure: BrigadeError | None = None):
        self.failure = failure

    def collect(self, environment, runtime, equipment) -> dict:
        if self.failure is not None:
            raise self.failure
        return {"merged": 3}


class BuiltInCollectorTest(unittest.TestCase):
    def test_should_answer_the_document_of_the_module_as_json(self):
        # Arrange
        collector = BuiltInCollector(
            name="pr-list", source="built-in", command="pr_list", module=CollectingModuleDouble()
        )

        # Act
        answer = collector.collect({}, None, NO_EQUIPMENT)

        # Assert
        self.assertEqual(answer.exit_code, 0)
        self.assertEqual(answer.stdout, '{"merged": 3}')
        self.assertEqual(answer.stderr, "")

    def test_should_answer_a_failure_of_the_module_on_stderr(self):
        # Arrange
        module = CollectingModuleDouble(BrigadeError("gh is not logged in"))
        collector = BuiltInCollector(name="pr-list", source="built-in", command="pr_list", module=module)

        # Act
        answer = collector.collect({}, None, NO_EQUIPMENT)

        # Assert
        self.assertEqual(answer.exit_code, 1)
        self.assertEqual(answer.stdout, "")
        self.assertEqual(answer.stderr, "gh is not logged in\n")
