import argparse
import tempfile
import unittest
from pathlib import Path

from brigade.commands.note import COMMAND, note
from brigade.errors import BrigadeError
from brigade.inbox.read_inbox import Signal, read_inbox
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

NO_PROJECT = None


class NoteTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        write_operational_corpus(root)
        self.processes = ScriptedProcesses()
        self.runtime = create_test_runtime(create_test_paths(root), run_process=self.processes)
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})

    def test_should_record_the_note_in_the_inbox(self):
        # Arrange
        request = argparse.Namespace(text="fix the flaky test", project=NO_PROJECT)

        # Act
        note(request, self.runtime)

        # Assert
        self.assertEqual(
            read_inbox(self.runtime.paths.state_root, FIXED_NOW),
            (
                Signal(
                    id="8b0cc9f9e16ac54d1c1ce4b203c20d56e7721576ee987093d40d148087701487",
                    fingerprint="note:57e52f352e5e",
                    kind="note",
                    project=None,
                    count=1,
                    age_s=0,
                    status="new",
                    evidence={"text": "fix the flaky test"},
                ),
            ),
        )

    def test_should_answer_the_signal_of_the_note_on_a_registered_project(self):
        # Arrange
        request = argparse.Namespace(text="fix the flaky test", project="oak")

        # Act
        document = note(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "signal": "a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
                "fingerprint": "note:474fa40ae4db",
            },
        )

    def test_should_refuse_a_project_that_is_not_registered(self):
        # Arrange
        request = argparse.Namespace(text="fix the flaky test", project="elm")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            note(request, self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), "@PROJECT.elm is not registered")

    def test_should_record_nothing_for_a_project_that_is_not_registered(self):
        # Arrange
        request = argparse.Namespace(text="fix the flaky test", project="elm")

        # Act
        with self.assertRaises(BrigadeError):
            note(request, self.runtime)

        # Assert
        self.assertEqual(read_inbox(self.runtime.paths.state_root, FIXED_NOW), ())


class NoteBeforeInitTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=ScriptedProcesses())

    def test_should_refuse_a_project_naming_it_as_not_registered(self):
        # Arrange
        request = argparse.Namespace(text="fix the flaky test", project="nope")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            note(request, self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), "@PROJECT.nope is not registered")


class NoteTextTest(unittest.TestCase):
    def test_should_name_the_signal_it_recorded(self):
        # Arrange
        document = {
            "schema_version": 1,
            "signal": "a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
            "fingerprint": "note:474fa40ae4db",
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "recorded a4a5f46 note:474fa40ae4db")
