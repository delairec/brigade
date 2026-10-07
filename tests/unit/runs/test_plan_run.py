import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brigade.corpus.read_entity import Entity, EntityField
from brigade.errors import BrigadeError, UsageError
from brigade.runs.plan_run import (
    RunRequest,
    _choose_run_id,
    _locate_cwd,
    _read_argument,
    _read_brief,
    _read_role_binding,
    plan_run,
)


def make_project(name: str, fields: tuple = ()) -> Entity:
    return Entity(name=name, fields=fields)


class ReadRoleBindingTest(unittest.TestCase):
    def test_should_raise_when_the_binding_is_not_slot_equals_name(self):
        # Arrange
        project = make_project("alpha")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            _read_role_binding(project, "no-separator")

        # Assert
        self.assertEqual(str(raised.exception), "@PROJECT.alpha has ROLE no-separator, not slot=name")

    def test_should_raise_when_the_slot_is_empty(self):
        # Arrange
        project = make_project("alpha")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            _read_role_binding(project, "=name")

        # Assert
        self.assertEqual(str(raised.exception), "@PROJECT.alpha has ROLE =name, not slot=name")

    def test_should_raise_when_the_name_is_empty(self):
        # Arrange
        project = make_project("alpha")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            _read_role_binding(project, "slot=")

        # Assert
        self.assertEqual(str(raised.exception), "@PROJECT.alpha has ROLE slot=, not slot=name")

    def test_should_parse_a_valid_binding(self):
        # Arrange
        project = make_project("alpha")

        # Act
        slot, name = _read_role_binding(project, "plan=bastien")

        # Assert
        self.assertEqual((slot, name), ("plan", "bastien"))


class LocateCwdTest(unittest.TestCase):
    def test_should_use_the_current_directory_when_no_cwd_and_no_project_path(self):
        # Act
        directory = _locate_cwd(None, None)

        # Assert
        self.assertEqual(directory, Path.cwd())

    def test_should_raise_when_the_directory_does_not_exist(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            _locate_cwd("/nonexistent-directory-xyz", None)

        # Assert
        self.assertIn("no directory", str(raised.exception))

    def test_should_use_the_project_path_when_no_cwd_is_given(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        project = make_project("alpha", (EntityField(name="PATH", value=root.name),))

        # Act
        directory = _locate_cwd(None, project)

        # Assert
        self.assertEqual(directory, Path(root.name))


class ReadBriefTest(unittest.TestCase):
    def test_should_return_none_when_no_brief_is_given(self):
        # Act
        path, text = _read_brief(None)

        # Assert
        self.assertEqual((path, text), (None, None))

    def test_should_raise_when_the_brief_file_does_not_exist(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            _read_brief("/nonexistent-brief-xyz.md")

        # Assert
        self.assertIn("no brief file", str(raised.exception))

    def test_should_read_the_brief_file(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name) / "brief.md"
        path.write_text("Deliver the task.")

        # Act
        brief_path, text = _read_brief(str(path))

        # Assert
        self.assertEqual(brief_path, path)
        self.assertEqual(text, "Deliver the task.")


class ReadArgumentTest(unittest.TestCase):
    def test_should_raise_when_the_argument_is_not_key_equals_value(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            _read_argument("no-separator")

        # Assert
        self.assertEqual(str(raised.exception), "the argument no-separator is not key=value")

    def test_should_raise_when_the_key_is_empty(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            _read_argument("=value")

        # Assert
        self.assertEqual(str(raised.exception), "the argument =value is not key=value")

    def test_should_parse_a_valid_argument(self):
        # Act
        key, value = _read_argument("name=value")

        # Assert
        self.assertEqual((key, value), ("name", "value"))


class ChooseRunIdTest(unittest.TestCase):
    def test_should_create_a_run_id_when_none_is_given(self):
        # Arrange
        runtime = mock.Mock()
        runtime.now = mock.Mock()

        # Act
        with mock.patch("brigade.runs.plan_run.create_run_id", return_value="20261007T120000Z-abcdef"):
            run_id = _choose_run_id(None, runtime)

        # Assert
        self.assertEqual(run_id, "20261007T120000Z-abcdef")

    def test_should_raise_when_the_run_id_does_not_match_the_pattern(self):
        # Arrange
        runtime = mock.Mock()

        # Act
        with self.assertRaises(UsageError) as raised:
            _choose_run_id("not-a-run-id", runtime)

        # Assert
        self.assertEqual(str(raised.exception), "not-a-run-id is not a run id")

    def test_should_accept_a_valid_run_id(self):
        # Arrange
        runtime = mock.Mock()

        # Act
        run_id = _choose_run_id("20261007T120000Z-abcdef", runtime)

        # Assert
        self.assertEqual(run_id, "20261007T120000Z-abcdef")


class PlanRunWhenNoClientIsConfiguredTest(unittest.TestCase):
    def test_should_raise_naming_the_configuration_file(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        config_root = Path(root.name) / "brigade"
        config_root.mkdir(parents=True)
        configuration_path = config_root / "config.toml"
        configuration_path.write_text("")
        runtime = mock.Mock()
        runtime.paths.config_root = config_root
        request = RunRequest(
            procedure="review",
            slot="plan",
            project=None,
            cwd=None,
            brief=None,
            arguments=(),
            run_id=None,
        )

        # Act
        with self.assertRaises(BrigadeError) as raised:
            plan_run(request, runtime)

        # Assert
        self.assertEqual(
            str(raised.exception),
            f"config.toml names no client: set the client key in {configuration_path}",
        )
