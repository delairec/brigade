import json
import tempfile
import unittest
from pathlib import Path

from brigade.errors import CannotWrite
from brigade.mining.read_text_scrubber import read_text_scrubber
from brigade.system.process_trace import ProcessTrace
from brigade.system.stderr_masker import StderrMasker
from brigade.system.trail_writer import TrailWriter
from tests.unit.keep_stderr_as_is import keep_stderr_as_is
from tests.unit.scripted_processes import ScriptedProcesses

GIT_VERSION = ProcessTrace(("git", "--version"), "/", "exited", 0, 3)
AWAWA_LINT = ProcessTrace(("awawa", "lint"), "/", "exited", 1, 40)


class TrailWriterTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.destination = Path(self.root.name) / "commands" / "20261007T120000Z-doctor.jsonl"
        self.reported = []
        self.trail = TrailWriter(self.reported.append, keep_stderr_as_is)

    def read_lines(self) -> list:
        return list(map(json.loads, self.destination.read_text().splitlines()))


class TrailWriterLocatedTest(TrailWriterTestCase):
    def test_should_create_the_trail_before_any_record(self):
        # Act
        self.trail.locate(self.destination)

        # Assert
        self.assertEqual(self.destination.read_text(), "")

    def test_should_append_one_line_per_record(self):
        # Arrange
        self.trail.locate(self.destination)

        # Act
        self.trail.append(GIT_VERSION)

        # Assert
        self.assertEqual(
            self.read_lines(),
            [
                {
                    "schema_version": 1,
                    "argv": ["git", "--version"],
                    "cwd": "/",
                    "exit": 0,
                    "duration_ms": 3,
                    "outcome": "exited",
                }
            ],
        )

    def test_should_report_each_record_it_appends(self):
        # Arrange
        self.trail.locate(self.destination)

        # Act
        self.trail.append(GIT_VERSION)

        # Assert
        self.assertEqual(self.reported, [GIT_VERSION])


class TrailWriterNotYetLocatedTest(TrailWriterTestCase):
    def test_should_write_the_records_it_held_where_it_is_located_then(self):
        # Arrange
        self.trail.append(GIT_VERSION)
        self.trail.append(AWAWA_LINT)

        # Act
        self.trail.locate(self.destination)

        # Assert
        self.assertEqual(
            self.read_lines(),
            [
                {
                    "schema_version": 1,
                    "argv": ["git", "--version"],
                    "cwd": "/",
                    "exit": 0,
                    "duration_ms": 3,
                    "outcome": "exited",
                },
                {
                    "schema_version": 1,
                    "argv": ["awawa", "lint"],
                    "cwd": "/",
                    "exit": 1,
                    "duration_ms": 40,
                    "outcome": "exited",
                },
            ],
        )

    def test_should_settle_the_records_it_held_on_the_fallback(self):
        # Arrange
        self.trail.append(GIT_VERSION)

        # Act
        self.trail.settle(self.destination)

        # Assert
        self.assertEqual(
            self.read_lines(),
            [
                {
                    "schema_version": 1,
                    "argv": ["git", "--version"],
                    "cwd": "/",
                    "exit": 0,
                    "duration_ms": 3,
                    "outcome": "exited",
                }
            ],
        )

    def test_should_settle_nothing_when_it_held_no_record(self):
        # Act
        self.trail.settle(self.destination)

        # Assert
        self.assertFalse(self.destination.exists())


class TrailWriterAlreadyLocatedTest(TrailWriterTestCase):
    def test_should_keep_its_trail_when_settled(self):
        # Arrange
        fallback = self.destination.with_name("20261007T120000Z-run.jsonl")
        self.trail.locate(self.destination)
        self.trail.append(GIT_VERSION)

        # Act
        self.trail.settle(fallback)

        # Assert
        self.assertEqual(
            self.read_lines(),
            [
                {
                    "schema_version": 1,
                    "argv": ["git", "--version"],
                    "cwd": "/",
                    "exit": 0,
                    "duration_ms": 3,
                    "outcome": "exited",
                }
            ],
        )
        self.assertEqual(fallback.exists(), False)


class TrailWriterThatCannotWriteTest(TrailWriterTestCase):
    def test_should_refuse_a_destination_it_cannot_write(self):
        # Arrange
        blocked = Path(self.root.name) / "blocked"
        blocked.mkdir()

        # Act
        with self.assertRaises(CannotWrite) as raised:
            self.trail.locate(blocked)

        # Assert
        self.assertEqual(str(raised.exception), f"cannot write {blocked}: Is a directory")


class TrailWriterOfAFailedProcessTest(TrailWriterTestCase):
    def test_should_write_its_stderr_masked(self):
        # Arrange
        trail = TrailWriter(self.reported.append, {"fatal: Acme refused": "fatal: [private] refused"}.__getitem__)
        trail.locate(self.destination)

        # Act
        trail.append(ProcessTrace(("git", "push"), "/", "exited", 1, 30, stderr="fatal: Acme refused"))

        # Assert
        self.assertEqual(self.read_lines()[0]["stderr"], "fatal: [private] refused")

    def test_should_leave_no_token_and_no_identifier_a_private_pattern_or_a_built_in_matches(self):
        # Arrange
        config_root = Path(self.root.name) / "config"
        processes = ScriptedProcesses()
        processes.answer_entities(
            config_root,
            "PROJECT",
            {
                "oak": (("PATH", "/srv/oak"), ("PRIVATE", r"Acme\w*"), ("PUBLIC", "AcmeOpen")),
                "elm": (("PATH", "/srv/elm"), ("PRIVATE", "Zorg")),
            },
        )
        masker = StderrMasker(lambda: read_text_scrubber(processes, config_root))
        trail = TrailWriter(self.reported.append, masker.mask)
        trail.locate(self.destination)
        stderr = (
            "remote: ghp_fixture1 gho_fixture2 ghs_fixture3 github_pat_fixture_4 refused for AcmeBilling\n"
            "error: sk-ant-fixture-5 of Zorg rejected, see /home/alice/.claude/s1.jsonl or ask ada@example.org\n"
            "hint: AcmeOpen stays public\n"
        )

        # Act
        trail.append(ProcessTrace(("git", "push"), "/srv/oak", "exited", 1, 30, stderr=stderr))

        # Assert
        self.assertEqual(
            self.read_lines()[0]["stderr"],
            "remote: [GitHub token] [GitHub token] [GitHub token] [GitHub token] refused for [private]\n"
            "error: [Anthropic API key] of [private] rejected, see [home path]/.claude/s1.jsonl or ask [e-mail address]\n"
            "hint: AcmeOpen stays public\n",
        )
