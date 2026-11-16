import argparse
import contextlib
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.preflight_add import COMMAND, preflight_add
from brigade.errors import BrigadeError, CorpusLintFailed
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

NOT_DEFINED = ProcessAnswer(exit_code=1, stderr="awawa show: @PREFLIGHT.nightly is not defined in the workspace\n")
DECLARED = ProcessAnswer()
NOT_DECLARED = ProcessAnswer(exit_code=1, stderr="awawa show: PREFLIGHT is not a type of the workspace\n")
CLEAN = ProcessAnswer()
FINDINGS = ProcessAnswer(exit_code=1, stdout="preflights.awawa:3:2 L003 error unknown field\n")
NIGHTLY_ENTITY = {
    "fields": [
        {"name": "TITLE", "atoms": ['"the nightly checks of the shop"'], "fields": []},
        {"name": "CHECK", "atoms": ['"coverage"'], "fields": []},
    ]
}
NIGHTLY_BLOCK = 'PREFLIGHT nightly\n\tTITLE "the nightly checks of the shop"\n\tCHECK "coverage"\n'
NIGHTLY_FILE = (
    "schema_version = 1\n"
    'name = "nightly"\n'
    'description = "the nightly checks of the shop"\n'
    "collectors = []\n"
    'checks = [{ name = "coverage" }]\n'
)


def place_executable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755)


class PreflightAddTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name).resolve()
        self.project = root / "shop"
        place_executable(self.project / ".brigade" / "collectors" / "notes")
        place_executable(self.project / ".brigade" / "checks" / "coverage")
        self.enterContext(contextlib.chdir(self.project))
        self.paths = create_test_paths(root)
        self.paths.config_root.mkdir(parents=True)

    def add(self, mode: str, answers: dict, step: str = "notes") -> tuple[RecordingProcessRunner, dict]:
        runner = RecordingProcessRunner(
            {
                ("git", "rev-parse", "--show-toplevel"): ProcessAnswer(stdout=f"{self.project}\n"),
                ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): ProcessAnswer(
                    stdout=f"{self.project / '.git'}\n"
                ),
                **create_registry_answers(self.paths.config_root, {"shop": {"PATH": str(self.project), "MODE": mode}}),
                **answers,
            }
        )
        request = argparse.Namespace(name="nightly", step=step, extra_arguments=["depth=1"])
        self.runner = runner
        return runner, preflight_add(request, create_test_runtime(self.paths, run_process=runner))

    def corpus_answers(self, *, declared: ProcessAnswer, entity: ProcessAnswer, lint: ProcessAnswer) -> dict:
        project = str(self.project)
        return {
            ("awawa", "show", "PREFLIGHT", project): declared,
            ("awawa", "show", "@PREFLIGHT.nightly", "--json", project): entity,
            ("awawa", "lint", "--strict", project): lint,
        }

    def test_should_write_a_new_preflight_entity_then_format_it_and_lint_the_corpus_committing_nothing(self):
        # Arrange
        answers = self.corpus_answers(declared=DECLARED, entity=NOT_DEFINED, lint=CLEAN)

        # Act
        runner, _document = self.add("control", answers)

        # Assert
        self.assertEqual(
            (self.project / "preflights.awawa").read_text(),
            'PREFLIGHT nightly\n\tTITLE "the custom preflight nightly"\n\tCOLLECTOR "notes"\n\t\tPARAMETER "depth=1"\n',
        )
        self.assertEqual(
            runner.list_argvs(),
            [
                ("git", "rev-parse", "--show-toplevel"),
                ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"),
                ("awawa", "status", "PROJECT", "--json", str(self.paths.config_root)),
                ("awawa", "show", "@PROJECT.shop", "--json", str(self.paths.config_root)),
                ("awawa", "show", "PREFLIGHT", str(self.project)),
                ("awawa", "show", "@PREFLIGHT.nightly", "--json", str(self.project)),
                ("awawa", "fmt", str(self.project / "preflights.awawa")),
                ("awawa", "lint", "--strict", str(self.project)),
            ],
        )

    def test_should_add_the_step_to_the_preflight_entity_the_corpus_already_holds(self):
        # Arrange
        (self.project / "preflights.awawa").write_text(NIGHTLY_BLOCK)
        entity = ProcessAnswer(stdout=json.dumps({"file": str(self.project / "preflights.awawa"), **NIGHTLY_ENTITY}))
        answers = self.corpus_answers(declared=DECLARED, entity=entity, lint=CLEAN)

        # Act
        self.add("control", answers)

        # Assert
        self.assertEqual(
            (self.project / "preflights.awawa").read_text(),
            'PREFLIGHT nightly\n\tTITLE "the nightly checks of the shop"\n\tCOLLECTOR "notes"\n\t\tPARAMETER "depth=1"\n'
            '\tCHECK "coverage"\n',
        )

    def test_should_add_the_step_to_the_preflight_entity_in_the_file_of_the_corpus_that_holds_it(self):
        # Arrange
        gates = self.project / "gates.awawa"
        gates.write_text(NIGHTLY_BLOCK)
        entity = ProcessAnswer(stdout=json.dumps({"file": str(gates), **NIGHTLY_ENTITY}))
        answers = self.corpus_answers(declared=DECLARED, entity=entity, lint=CLEAN)

        # Act
        runner, document = self.add("control", answers)

        # Assert
        self.assertEqual(
            (
                gates.read_text(),
                (self.project / "preflights.awawa").exists(),
                document["file"],
                runner.list_argvs()[-2],
            ),
            (
                (
                    'PREFLIGHT nightly\n\tTITLE "the nightly checks of the shop"\n\tCOLLECTOR "notes"\n'
                    '\t\tPARAMETER "depth=1"\n\tCHECK "coverage"\n'
                ),
                False,
                str(gates),
                ("awawa", "fmt", str(gates)),
            ),
        )

    def test_should_restore_the_file_it_wrote_when_the_lint_of_the_corpus_fails(self):
        # Arrange
        answers = self.corpus_answers(declared=DECLARED, entity=NOT_DEFINED, lint=FINDINGS)

        # Act
        with self.assertRaises(CorpusLintFailed):
            self.add("control", answers)

        # Assert
        self.assertEqual(
            self.runner.list_argvs()[-3:],
            [
                ("git", "ls-tree", "--name-only", "HEAD", "--", "preflights.awawa"),
                ("git", "rm", "--cached", "--quiet", "--ignore-unmatch", "--", "preflights.awawa"),
                ("git", "clean", "--force", "--quiet", "--", "preflights.awawa"),
            ],
        )

    def test_should_refuse_a_corpus_that_declares_no_preflight_naming_the_type_and_write_nothing(self):
        # Arrange
        answers = self.corpus_answers(declared=NOT_DECLARED, entity=NOT_DEFINED, lint=CLEAN)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            self.add("control", answers)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            f"the corpus of the project at {self.project} declares no PREFLIGHT; add SCHEMA PREFLIGHT to it",
        )
        self.assertFalse((self.project / "preflights.awawa").exists())

    def test_should_refuse_a_step_that_resolves_as_no_collector_and_no_check_before_writing_anything(self):
        # Arrange
        answers = self.corpus_answers(declared=DECLARED, entity=NOT_DEFINED, lint=CLEAN)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            self.add("control", answers, step="nope")

        # Assert
        self.assertEqual(str(refusal.exception), "no collector and no check nope")
        self.assertFalse((self.project / "preflights.awawa").exists())

    def test_should_write_a_new_toml_file_on_a_project_without_a_corpus_committing_nothing(self):
        # Act
        runner, _document = self.add("none", {}, step="coverage")

        # Assert
        self.assertEqual(
            (self.project / ".brigade" / "preflights" / "nightly.toml").read_text(),
            "schema_version = 1\n"
            'name = "nightly"\n'
            'description = "the custom preflight nightly"\n'
            "collectors = [\n"
            "]\n"
            "checks = [\n"
            '    { name = "coverage", parameters = { "depth" = "1" } },\n'
            "]\n",
        )
        self.assertEqual(
            runner.list_argvs(),
            [
                ("git", "rev-parse", "--show-toplevel"),
                ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"),
                ("awawa", "status", "PROJECT", "--json", str(self.paths.config_root)),
                ("awawa", "show", "@PROJECT.shop", "--json", str(self.paths.config_root)),
            ],
        )

    def test_should_add_the_step_to_the_toml_file_the_project_already_holds(self):
        # Arrange
        (self.project / ".brigade" / "preflights").mkdir(parents=True)
        (self.project / ".brigade" / "preflights" / "nightly.toml").write_text(NIGHTLY_FILE)

        # Act
        self.add("none", {})

        # Assert
        self.assertEqual(
            (self.project / ".brigade" / "preflights" / "nightly.toml").read_text(),
            "schema_version = 1\n"
            'name = "nightly"\n'
            'description = "the nightly checks of the shop"\n'
            "collectors = [\n"
            '    { name = "notes", parameters = { "depth" = "1" } },\n'
            "]\n"
            "checks = [\n"
            '    { name = "coverage", parameters = {} },\n'
            "]\n",
        )

    def test_should_refuse_a_toml_file_that_is_no_preflight_and_leave_it_as_it_was(self):
        # Arrange
        (self.project / ".brigade" / "preflights").mkdir(parents=True)
        (self.project / ".brigade" / "preflights" / "nightly.toml").write_text('name = "nightly"\n')

        # Act
        with self.assertRaises(BrigadeError):
            self.add("none", {})

        # Assert
        self.assertEqual((self.project / ".brigade" / "preflights" / "nightly.toml").read_text(), 'name = "nightly"\n')

    def refuse_unreadable_parameter(self) -> BrigadeError:
        request = argparse.Namespace(name="nightly", step="coverage", extra_arguments=["note=a\x7fb"])
        runner = RecordingProcessRunner(
            {
                ("git", "rev-parse", "--show-toplevel"): ProcessAnswer(stdout=f"{self.project}\n"),
                ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): ProcessAnswer(
                    stdout=f"{self.project / '.git'}\n"
                ),
                **create_registry_answers(
                    self.paths.config_root, {"shop": {"PATH": str(self.project), "MODE": "none"}}
                ),
            }
        )
        with self.assertRaises(BrigadeError) as refusal:
            preflight_add(request, create_test_runtime(self.paths, run_process=runner))
        return refusal.exception

    def test_should_refuse_a_toml_file_its_lint_refuses_once_written_and_remove_it(self):
        # Act
        refusal = self.refuse_unreadable_parameter()

        # Assert
        file = self.project / ".brigade" / "preflights" / "nightly.toml"
        self.assertRegex(str(refusal), f"^the preflight file {file} is no TOML document: ")
        self.assertFalse(file.exists())

    def test_should_restore_the_toml_file_the_project_held_when_its_lint_refuses_the_file_written(self):
        # Arrange
        file = self.project / ".brigade" / "preflights" / "nightly.toml"
        file.parent.mkdir(parents=True)
        file.write_text(NIGHTLY_FILE)

        # Act
        self.refuse_unreadable_parameter()

        # Assert
        self.assertEqual(file.read_text(), NIGHTLY_FILE)


class PreflightAddRenderingTest(unittest.TestCase):
    def test_should_print_the_step_added_and_the_file_written(self):
        # Arrange
        document = {
            "schema_version": 1,
            "preflight": "nightly",
            "step": {"kind": "collector", "name": "notes", "parameters": {"depth": "1"}},
            "file": "/srv/shop/preflights.awawa",
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "added the collector notes to the preflight nightly in /srv/shop/preflights.awawa")
