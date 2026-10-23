import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from brigade.collecting.collect_document import Collection, CollectionRequest, collect_document
from brigade.collecting.collector_environment import CollectorInputs
from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.errors import BrigadeError
from brigade.system.parse_configuration import Configuration
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

CACHE_KEY = "cdfce1be6a8703b24e8c5f9ef26d0702fcbabee709441769d8e27941e3ccc852"
CACHED_DOCUMENT = {
    "schema_version": 1,
    "collector": "weather",
    "collected_at": "2026-10-19T09:00:00Z",
    "cache": True,
    "summary": {"days": 1},
    "items": ["rain"],
}
SNOWY_CACHED_DOCUMENT = {
    "schema_version": 1,
    "collector": "weather",
    "collected_at": "2026-10-19T09:00:00Z",
    "cache": True,
    "summary": {"days": 1},
    "items": ["snow"],
}
FRESH_DOCUMENT = {
    "schema_version": 1,
    "collector": "weather",
    "collected_at": "2026-10-19T09:00:00Z",
    "summary": {"days": 1},
    "items": ["sun"],
}
MISSHAPEN_DOCUMENT = {
    "schema_version": 1,
    "collector": "weather",
    "collected_at": "2026-10-19T09:00:00Z",
    "summary": {"days": 1},
    "items": "sun",
}
INPUTS = CollectorInputs(project=Path("/srv/oak"), since=date(2026, 10, 1), parameters={"city": "Lyon"})
EQUIPMENT = CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github")


class CollectorDouble:
    def __init__(self, exit_code: int, stdout: str, stderr: str = ""):
        self.name = "weather"
        self.command = "brigade-collector-weather"
        self.environments = []
        self._answer = SimpleNamespace(exit_code=exit_code, stdout=stdout, stderr=stderr, duration_ms=40)

    def collect(self, environment: dict, runtime, equipment) -> SimpleNamespace:
        self.environments.append(environment)
        return self._answer


def create_request(*, refresh: bool = False) -> CollectionRequest:
    return CollectionRequest(inputs=INPUTS, refresh=refresh, equipment=EQUIPMENT)


class CollectDocumentTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=ScriptedProcesses())
        self.cache_entry = self.root / "cache" / "collectors" / "weather" / CACHE_KEY

    def test_should_keep_a_document_declaring_itself_cacheable_in_the_cache(self):
        # Arrange
        collector = CollectorDouble(0, json.dumps(CACHED_DOCUMENT))

        # Act
        collection = collect_document(collector, create_request(), self.runtime)

        # Assert
        self.assertEqual(
            collection,
            Collection(document_path=self.cache_entry / "document.json", document=CACHED_DOCUMENT, cached=False),
        )

    def test_should_record_beside_the_cached_document_how_it_was_collected(self):
        # Arrange
        collector = CollectorDouble(0, json.dumps(CACHED_DOCUMENT))

        # Act
        collect_document(collector, create_request(), self.runtime)

        # Assert
        self.assertEqual(
            json.loads((self.cache_entry / "sidecar.json").read_text(encoding="utf-8")),
            {
                "schema_version": 1,
                "collector": "weather",
                "command": "brigade-collector-weather",
                "parameters": {"city": "Lyon"},
                "since": "2026-10-01",
                "duration_ms": 40,
                "exit_code": 0,
                "cache_key": CACHE_KEY,
            },
        )

    def test_should_hand_the_collector_its_inputs_as_environment_variables(self):
        # Arrange
        collector = CollectorDouble(0, json.dumps(CACHED_DOCUMENT))

        # Act
        collect_document(collector, create_request(), self.runtime)

        # Assert
        self.assertEqual(
            collector.environments,
            [{"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "2026-10-01", "BRIGADE_PARAMS": '{"city": "Lyon"}'}],
        )

    def test_should_answer_from_the_cache(self):
        # Arrange
        collect_document(CollectorDouble(0, json.dumps(CACHED_DOCUMENT)), create_request(), self.runtime)

        # Act
        collection = collect_document(
            CollectorDouble(0, json.dumps(SNOWY_CACHED_DOCUMENT)), create_request(), self.runtime
        )

        # Assert
        self.assertEqual(
            collection,
            Collection(document_path=self.cache_entry / "document.json", document=CACHED_DOCUMENT, cached=True),
        )

    def test_should_not_run_the_collector_when_the_cache_answers(self):
        # Arrange
        collect_document(CollectorDouble(0, json.dumps(CACHED_DOCUMENT)), create_request(), self.runtime)
        second_collector = CollectorDouble(0, json.dumps(SNOWY_CACHED_DOCUMENT))

        # Act
        collect_document(second_collector, create_request(), self.runtime)

        # Assert
        self.assertEqual(second_collector.environments, [])

    def test_should_collect_again_when_a_refresh_is_asked(self):
        # Arrange
        collect_document(CollectorDouble(0, json.dumps(CACHED_DOCUMENT)), create_request(), self.runtime)

        # Act
        collection = collect_document(
            CollectorDouble(0, json.dumps(SNOWY_CACHED_DOCUMENT)), create_request(refresh=True), self.runtime
        )

        # Assert
        self.assertEqual(
            collection,
            Collection(document_path=self.cache_entry / "document.json", document=SNOWY_CACHED_DOCUMENT, cached=False),
        )

    def test_should_keep_a_document_fresh_at_each_call_in_the_state_directory(self):
        # Arrange
        collector = CollectorDouble(0, json.dumps(FRESH_DOCUMENT))

        # Act
        collection = collect_document(collector, create_request(), self.runtime)

        # Assert
        self.assertEqual(
            collection,
            Collection(
                document_path=self.root / "state" / "collect" / "weather" / "document.json",
                document=FRESH_DOCUMENT,
                cached=False,
            ),
        )

    def test_should_keep_a_document_fresh_at_each_call_in_the_run_directory_of_a_run(self):
        # Arrange
        write_operational_corpus(self.root)
        runtime = create_test_runtime(
            create_test_paths(self.root, run_directory=self.root / "run"), run_process=ScriptedProcesses()
        )

        # Act
        collection = collect_document(CollectorDouble(0, json.dumps(FRESH_DOCUMENT)), create_request(), runtime)

        # Assert
        self.assertEqual(collection.document_path, self.root / "run" / "collect" / "weather" / "document.json")

    def test_should_answer_a_cached_document_from_its_copy_in_the_run_directory_of_a_run(self):
        # Arrange
        write_operational_corpus(self.root)
        runtime = create_test_runtime(
            create_test_paths(self.root, run_directory=self.root / "run"), run_process=ScriptedProcesses()
        )
        collect_document(CollectorDouble(0, json.dumps(CACHED_DOCUMENT)), create_request(), runtime)

        # Act
        collection = collect_document(CollectorDouble(0, json.dumps(CACHED_DOCUMENT)), create_request(), runtime)

        # Assert
        self.assertEqual(
            collection,
            Collection(
                document_path=self.root / "run" / "collect" / "weather" / "document.json",
                document=CACHED_DOCUMENT,
                cached=True,
            ),
        )

    def test_should_copy_a_cached_document_into_the_run_directory_of_a_run(self):
        # Arrange
        write_operational_corpus(self.root)
        runtime = create_test_runtime(
            create_test_paths(self.root, run_directory=self.root / "run"), run_process=ScriptedProcesses()
        )
        collect_document(CollectorDouble(0, json.dumps(CACHED_DOCUMENT)), create_request(), runtime)

        # Act
        collect_document(CollectorDouble(0, json.dumps(CACHED_DOCUMENT)), create_request(), runtime)

        # Assert
        copy = self.root / "run" / "collect" / "weather" / "document.json"
        self.assertEqual(json.loads(copy.read_text(encoding="utf-8")), CACHED_DOCUMENT)


class CollectDocumentRefusalTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=ScriptedProcesses())

    def test_should_report_a_collector_that_failed_with_the_tail_of_its_errors(self):
        # Arrange
        stderr = (
            "line 1\nline 2\nline 3\nline 4\nline 5\nline 6\nline 7\nline 8\nline 9\nline 10\nline 11\n"
            "line 12\nline 13\nline 14\nline 15\nline 16\nline 17\nline 18\nline 19\nline 20\nline 21\n"
        )
        collector = CollectorDouble(2, "", stderr)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            collect_document(collector, create_request(), self.runtime)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "collector weather exited 2\nline 2\nline 3\nline 4\nline 5\nline 6\nline 7\nline 8\nline 9\nline 10"
            "\nline 11\nline 12\nline 13\nline 14\nline 15\nline 16\nline 17\nline 18\nline 19\nline 20\nline 21",
        )

    def test_should_refuse_a_collector_that_printed_no_json(self):
        # Arrange
        collector = CollectorDouble(0, "sunny", "")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            collect_document(collector, create_request(), self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), "collector weather exited 0: it printed no JSON document")

    def test_should_refuse_a_document_outside_the_collector_shape(self):
        # Arrange
        collector = CollectorDouble(0, json.dumps(MISSHAPEN_DOCUMENT), "")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            collect_document(collector, create_request(), self.runtime)

        # Assert
        self.assertRegex(str(refusal.exception), r"^collector weather exited 0: its document .*items")
