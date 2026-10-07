import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brigade.errors import BrigadeError, ToolFailure, ToolNotFound
from brigade.roles.parse_role_file import RoleFile
from brigade.roles.resolve_role import (
    NO_PROJECT_BINDINGS,
    AgentLookup,
    RoleBindings,
    _find_named_agent,
    _list_directory_role_files,
    _locate_roleset,
    _read_agent,
    _read_role_file,
    resolve_role,
)


class ListDirectoryRoleFilesTest(unittest.TestCase):
    def test_should_return_an_empty_tuple_when_the_directory_does_not_exist(self):
        # Act
        paths = _list_directory_role_files(Path("/nonexistent-directory-xyz"))

        # Assert
        self.assertEqual(paths, ())

    def test_should_list_the_markdown_files_of_a_directory(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        (Path(root.name) / "a.md").touch()
        (Path(root.name) / "b.md").touch()
        (Path(root.name) / "c.txt").touch()

        # Act
        paths = _list_directory_role_files(Path(root.name))

        # Assert
        self.assertEqual([path.name for path in paths], ["a.md", "b.md"])


class LocateRolesetTest(unittest.TestCase):
    def test_should_return_the_absolute_directory_as_it_is(self):
        # Arrange
        bindings = RoleBindings(project="alpha", roles={}, roleset="/srv/roles", project_path=Path("/srv/alpha"))

        # Act
        directory = _locate_roleset(bindings)

        # Assert
        self.assertEqual(directory, Path("/srv/roles"))

    def test_should_return_the_directory_as_it_is_when_there_is_no_project_path(self):
        # Arrange
        bindings = RoleBindings(project="alpha", roles={}, roleset="roles", project_path=None)

        # Act
        directory = _locate_roleset(bindings)

        # Assert
        self.assertEqual(directory, Path("roles"))

    def test_should_resolve_a_relative_directory_against_the_project_path(self):
        # Arrange
        bindings = RoleBindings(project="alpha", roles={}, roleset="roles", project_path=Path("/srv/alpha"))

        # Act
        directory = _locate_roleset(bindings)

        # Assert
        self.assertEqual(directory, Path("/srv/alpha/roles"))


class ResolveRoleWhenNoRoleDeclaresTheSlotTest(unittest.TestCase):
    def test_should_raise_naming_the_slot(self):
        # Arrange
        runtime = mock.Mock()
        runtime.paths.config_root = Path("/nonexistent")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            resolve_role("nonexistent-slot", runtime, NO_PROJECT_BINDINGS)

        # Assert
        self.assertEqual(str(raised.exception), "no role declares the slot nonexistent-slot")


class ReadRoleFileWhenTheFileIsUnreadableTest(unittest.TestCase):
    def test_should_raise_naming_the_path_and_the_problem(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name) / "bad.md"
        path.write_text("no front matter at all")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            _read_role_file(path)

        # Assert
        self.assertIn(str(path), str(raised.exception))


class ReadAgentWhenTheFrontMatterHasProblemsTest(unittest.TestCase):
    def test_should_raise_naming_the_agent_and_the_problem(self):
        # Arrange
        runtime = mock.Mock()
        runtime.run_process = mock.Mock()
        entity = mock.Mock()
        entity.name = "broken"
        entity.fields = ()

        # Act
        with (
            mock.patch("brigade.roles.resolve_role.read_entity", return_value=entity),
            self.assertRaises(BrigadeError) as raised,
        ):
            _read_agent("broken", "plan", Path("/srv/corpus"), runtime)

        # Assert
        self.assertIn("@AGENT.broken", str(raised.exception))


class FindNamedAgentTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.config_path = Path(self.root.name) / "config.toml"
        self.config_path.write_text('instructions = "/srv/corpus"\n')
        self.runtime = mock.Mock()
        self.runtime.run_process = mock.Mock()
        self.lookup = AgentLookup(configuration_path=self.config_path, runtime=self.runtime)

    def test_should_return_none_when_no_instructions_corpus_is_set(self):
        # Arrange
        config_path = Path(self.root.name) / "empty.toml"
        config_path.write_text("")
        lookup = AgentLookup(configuration_path=config_path, runtime=self.runtime)

        # Act
        result = _find_named_agent(lookup, "plan", "bastien")

        # Assert
        self.assertIsNone(result)

    def test_should_reraise_tool_not_found(self):
        # Act
        with (
            mock.patch("brigade.roles.resolve_role._read_agent", side_effect=ToolNotFound("awawa not on PATH")),
            self.assertRaises(ToolNotFound),
        ):
            _find_named_agent(self.lookup, "plan", "bastien")

    def test_should_return_none_when_the_agent_read_fails(self):
        # Act
        with mock.patch("brigade.roles.resolve_role._read_agent", side_effect=ToolFailure("awawa failed")):
            result = _find_named_agent(self.lookup, "plan", "bastien")

        # Assert
        self.assertIsNone(result)

    def test_should_return_the_role_file_when_the_agent_is_read(self):
        # Arrange
        role_file = RoleFile(front_matter={"name": "bastien"}, body="Body.")

        # Act
        with mock.patch("brigade.roles.resolve_role._read_agent", return_value=role_file):
            result = _find_named_agent(self.lookup, "plan", "bastien")

        # Assert
        self.assertIs(result, role_file)
