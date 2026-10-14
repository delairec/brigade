import json
import os
import tempfile
import tomllib
import unittest
from pathlib import Path

from tests.awawa.provide_awawa import provide_awawa
from tests.cli.forward_coverage_environment import forward_coverage_environment
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, SHIPPED_SCHEMA, TemporaryMachine
from tests.process_launcher import ProcessLauncher

SCHEMA_ENTRY = 1
GITIGNORE_ENTRY = 2
CONFIGURATION_ENTRY = 3


class BrigadeInitOnAFreshMachineTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name))

    def tearDown(self):
        self.root.cleanup()

    def test_should_report_every_item_created_in_the_versioned_document(self):
        # Act
        completed = self.machine.run_init("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        corpus = self.machine.corpus
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "items": [
                    {"name": "repository", "path": str(corpus), "state": "created"},
                    {"name": "schema", "path": str(corpus / "_schema.awawa"), "state": "created"},
                    {"name": ".gitignore", "path": str(corpus / ".gitignore"), "state": "created"},
                    {"name": "config.toml", "path": str(corpus / "config.toml"), "state": "created"},
                ],
            },
        )

    def test_should_print_the_report_as_text(self):
        # Act
        completed = self.machine.run_init()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        corpus = self.machine.corpus
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                f"created  repository   {corpus}",
                f"created  schema       {corpus / '_schema.awawa'}",
                f"created  .gitignore   {corpus / '.gitignore'}",
                f"created  config.toml  {corpus / 'config.toml'}",
                "",
                "init: created 4 · present 0 · replaced 0 · differs 0",
            ],
        )

    def test_should_commit_the_schema_and_the_gitignore_in_one_commit_with_the_user_identity(self):
        # Arrange
        self.machine.run_init()

        # Act
        history = self.machine.read_git("log", "--format=%an <%ae>%n%s", "--name-only")

        # Assert
        self.assertEqual(
            history,
            "Ada Lovelace <ada@example.org>\nbrigade init: the operational corpus\n\n.gitignore\n_schema.awawa\n",
        )

    def test_should_install_the_shipped_schema(self):
        # Act
        self.machine.run_init()

        # Assert
        self.assertEqual((self.machine.corpus / "_schema.awawa").read_bytes(), SHIPPED_SCHEMA.read_bytes())

    def test_should_keep_the_configuration_out_of_the_repository(self):
        # Act
        self.machine.run_init()

        # Assert
        self.assertEqual((self.machine.corpus / ".gitignore").read_text(), "config.toml\n")

    def test_should_write_a_configuration_read_as_an_empty_table(self):
        # Arrange
        self.machine.run_init()

        # Act
        configuration = tomllib.loads((self.machine.corpus / "config.toml").read_text())

        # Assert
        self.assertEqual(configuration, {})

    def test_should_write_its_command_trail_alone_in_the_state_root_and_create_no_cache_root(self):
        # Act
        self.machine.run_init()

        # Assert
        self.assertEqual(
            [list((self.machine.state_home / "brigade").iterdir()), (self.machine.cache_home / "brigade").exists()],
            [[self.machine.state_home / "brigade" / "commands"], False],
        )

    def test_should_create_a_corpus_that_lints_clean(self):
        # Arrange
        provide_awawa(self)
        self.machine.run_init()

        # Act
        completed = ProcessLauncher.run(
            ["awawa", "lint", "--strict", str(self.machine.corpus)],
            cwd=self.machine.corpus,
            capture_output=True,
            text=True,
            check=False,
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


class BrigadeInitWithoutXdgVariablesTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name))

    def tearDown(self):
        self.root.cleanup()

    def test_should_create_the_corpus_under_the_home_configuration_directory(self):
        # Arrange
        home_only = {
            "PATH": self.machine.describe_environment()["PATH"],
            "HOME": str(self.machine.home),
            **forward_coverage_environment(),
        }

        # Act
        completed = self.machine.run_brigade(CLONE_ENTRY_POINT, "init", environment=home_only)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            sorted(path.name for path in (self.machine.home / ".config" / "brigade").iterdir()),
            [".git", ".gitignore", "_schema.awawa", "config.toml"],
        )


class BrigadeInitRunTwiceTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name))
        self.machine.run_init()

    def tearDown(self):
        self.root.cleanup()

    def test_should_report_every_item_present(self):
        # Act
        completed = self.machine.run_init("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            [item["state"] for item in json.loads(completed.stdout)["items"]],
            ["present", "present", "present", "present"],
        )

    def test_should_rewrite_nothing_and_commit_nothing(self):
        # Arrange
        corpus = self.machine.corpus
        written_files = [corpus / "_schema.awawa", corpus / ".gitignore", corpus / "config.toml"]
        modification_times = [path.stat().st_mtime_ns for path in written_files]

        # Act
        self.machine.run_init()

        # Assert
        self.assertEqual([path.stat().st_mtime_ns for path in written_files], modification_times)
        self.assertEqual(self.machine.read_git("rev-list", "--count", "HEAD"), "1\n")


class BrigadeInitWhenAFileDiffersFromTheShippedOneTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name))
        self.machine.run_init()

    def tearDown(self):
        self.root.cleanup()

    def test_should_leave_the_file_as_it_is_and_report_it_differing(self):
        # Arrange
        rows = [
            (".gitignore", ".gitignore", GITIGNORE_ENTRY),
            ("config.toml", "config.toml", CONFIGURATION_ENTRY),
        ]
        for name, file_name, entry in rows:
            with self.subTest(name=name):
                # Arrange
                edited_file = self.machine.corpus / file_name
                edited_file.write_text("# edited by the user\n")

                # Act
                completed = self.machine.run_init("--json")

                # Assert
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(
                    json.loads(completed.stdout)["items"][entry],
                    {"name": name, "path": str(edited_file), "state": "differs"},
                )
                self.assertEqual(edited_file.read_text(), "# edited by the user\n")

    def test_should_report_a_configuration_whose_trail_days_is_below_1_as_differing(self):
        # Arrange
        configuration = self.machine.corpus / "config.toml"
        configuration.write_text("trail_days = 0\n")

        # Act
        completed = self.machine.run_init("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["items"][CONFIGURATION_ENTRY],
            {"name": "config.toml", "path": str(configuration), "state": "differs"},
        )

    def test_should_print_a_warning_for_the_differing_file(self):
        # Arrange
        (self.machine.corpus / "config.toml").write_text('client = "fake"\n')

        # Act
        completed = self.machine.run_init()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        corpus = self.machine.corpus
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                f"present  repository   {corpus}",
                f"present  schema       {corpus / '_schema.awawa'}",
                f"present  .gitignore   {corpus / '.gitignore'}",
                f"differs  config.toml  {corpus / 'config.toml'}",
                "",
                "init: created 0 · present 3 · replaced 0 · differs 1",
                "warning: config.toml differs from the shipped file and is left as it is",
            ],
        )


class BrigadeInitWhenTheInstalledSchemaDiffersFromTheShippedOneTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name))
        self.machine.run_init()
        self.schema = self.machine.corpus / "_schema.awawa"
        self.schema.write_text("# an older schema\n")
        self.machine.read_git("commit", "--quiet", "--all", "--message", "an older schema")

    def tearDown(self):
        self.root.cleanup()

    def test_should_replace_it_with_the_shipped_schema_and_report_it_replaced(self):
        # Act
        completed = self.machine.run_init("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["items"][SCHEMA_ENTRY],
            {"name": "schema", "path": str(self.schema), "state": "replaced"},
        )
        self.assertEqual(self.schema.read_bytes(), SHIPPED_SCHEMA.read_bytes())

    def test_should_commit_the_replaced_schema(self):
        # Act
        self.machine.run_init()

        # Assert
        self.assertEqual(
            self.machine.read_git("log", "-1", "--format=%s", "--name-only"),
            "brigade init: the shipped schema\n\n_schema.awawa\n",
        )

    def test_should_count_the_replaced_schema_in_the_text_report(self):
        # Act
        completed = self.machine.run_init()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.splitlines()[-1], "init: created 0 · present 3 · replaced 1 · differs 0")


class BrigadeInitWhenTheSchemaIsMissingFromAnExistingRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name))
        self.machine.run_init()

    def tearDown(self):
        self.root.cleanup()

    def test_should_create_it_again_and_commit_it(self):
        # Arrange
        self.machine.read_git("rm", "--quiet", "_schema.awawa")
        self.machine.read_git("commit", "--quiet", "-m", "remove the schema")

        # Act
        completed = self.machine.run_init("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["items"][SCHEMA_ENTRY]["state"], "created")
        self.assertEqual(
            self.machine.read_git("log", "-1", "--format=%s", "--name-only"),
            "brigade init: the operational corpus\n\n_schema.awawa\n",
        )

    def test_should_create_it_again_without_a_commit_when_the_repository_still_holds_it(self):
        # Arrange
        (self.machine.corpus / "_schema.awawa").unlink()

        # Act
        completed = self.machine.run_init("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["items"][SCHEMA_ENTRY]["state"], "created")
        self.assertEqual(self.machine.read_git("rev-list", "--count", "HEAD"), "1\n")


class BrigadeInitWithoutAGitIdentityTest(unittest.TestCase):
    def test_should_exit_1_naming_the_missing_key_before_creating_anything(self):
        # Arrange
        rows = [
            (
                "user.name",
                "[user]\n\temail = ada@example.org\n",
                "brigade init: the git identity lacks user.name; set it with git config --global\n",
            ),
            (
                "user.email",
                "[user]\n\tname = Ada Lovelace\n",
                "brigade init: the git identity lacks user.email; set it with git config --global\n",
            ),
            (
                "both",
                "",
                "brigade init: the git identity lacks user.name and user.email; set it with git config --global\n",
            ),
        ]
        for missing, git_configuration, message in rows:
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as root:
                # Arrange
                machine = TemporaryMachine(Path(root), git_configuration)

                # Act
                completed = machine.run_init("--json")

                # Assert
                self.assertEqual(
                    (completed.returncode, completed.stdout, completed.stderr, machine.config_home.exists()),
                    (1, "", message, False),
                )


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class BrigadeInitWhereTheMachineRefusesTheConfigurationDirectoryTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name))
        self.machine.config_home.mkdir()

    def tearDown(self):
        self.machine.config_home.chmod(0o700)
        self.root.cleanup()

    def test_should_exit_1_naming_the_configuration_directory_it_cannot_create(self):
        # Arrange
        self.machine.config_home.chmod(0o500)

        # Act
        completed = self.machine.run_init()

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade init: cannot write {self.machine.corpus}: Permission denied\n"),
        )


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class BrigadeInitWhereTheMachineRefusesAFileOfTheCorpusTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name))
        self.machine.run_init()

    def tearDown(self):
        self.machine.corpus.chmod(0o700)
        self.root.cleanup()

    def test_should_exit_1_naming_the_file_it_cannot_create(self):
        # Arrange
        (self.machine.corpus / "config.toml").unlink()
        self.machine.corpus.chmod(0o500)

        # Act
        completed = self.machine.run_init()

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade init: cannot write {self.machine.corpus / 'config.toml'}: Permission denied\n"),
        )
