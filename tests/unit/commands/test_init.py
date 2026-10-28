import argparse
import tempfile
import tomllib
import unittest
from pathlib import Path

from brigade.commands.init import COMMAND, init
from brigade.corpus.shipped_data import SHIPPED_SCHEMA
from brigade.errors import BrigadeError, CannotWrite
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


def _create_git_answers(name: ProcessAnswer, email: ProcessAnswer) -> dict:
    return {
        ("git", "config", "--get", "user.name"): name,
        ("git", "config", "--get", "user.email"): email,
        ("git", "init"): ProcessAnswer(),
        ("git", "add"): ProcessAnswer(),
        ("git", "diff"): ProcessAnswer(exit_code=1),
        ("git", "commit"): ProcessAnswer(),
    }


class InitTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.runner = ScriptedProcessRunner(
            _create_git_answers(ProcessAnswer(stdout="Ada\n"), ProcessAnswer(stdout="ada@example.org\n"))
        )
        self.runtime = create_test_runtime(create_test_paths(Path(self.root.name)), run_process=self.runner.run)
        self.config_root = self.runtime.paths.config_root
        self.no_option = argparse.Namespace()

    def test_should_create_the_repository_and_its_shipped_files(self):
        # Act
        document = init(self.no_option, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "items": [
                    {"name": "repository", "path": str(self.config_root), "state": "created"},
                    {"name": "schema", "path": str(self.config_root / "_schema.awawa"), "state": "created"},
                    {"name": ".gitignore", "path": str(self.config_root / ".gitignore"), "state": "created"},
                    {"name": "config.toml", "path": str(self.config_root / "config.toml"), "state": "created"},
                ],
            },
        )

    def test_should_commit_the_schema_and_the_gitignore_it_created(self):
        # Act
        init(self.no_option, self.runtime)

        # Assert
        self.assertIn(("git", "add", "--", "_schema.awawa", ".gitignore"), self.runner.argvs)

    def test_should_commit_them_under_the_message_of_the_operational_corpus(self):
        # Act
        init(self.no_option, self.runtime)

        # Assert
        self.assertIn(("git", "commit", "--quiet", "-m", "brigade init: the operational corpus"), self.runner.argvs)

    def test_should_install_the_shipped_schema(self):
        # Act
        init(self.no_option, self.runtime)

        # Assert
        self.assertEqual((self.config_root / "_schema.awawa").read_bytes(), SHIPPED_SCHEMA.read_bytes())

    def test_should_keep_the_configuration_out_of_the_repository(self):
        # Act
        init(self.no_option, self.runtime)

        # Assert
        self.assertEqual((self.config_root / ".gitignore").read_text(), "config.toml\n")

    def test_should_write_a_configuration_read_as_an_empty_table(self):
        # Arrange
        init(self.no_option, self.runtime)

        # Act
        configuration = tomllib.loads((self.config_root / "config.toml").read_text())

        # Assert
        self.assertEqual(configuration, {})

    def test_should_document_the_port_of_the_dashboard_with_its_default(self):
        # Arrange
        init(self.no_option, self.runtime)

        # Act
        content = (self.config_root / "config.toml").read_text()

        # Assert
        self.assertIn("\n# dashboard_port = 8470\n", content)

    def test_should_document_the_quota_window_with_its_default(self):
        # Arrange
        init(self.no_option, self.runtime)

        # Act
        content = (self.config_root / "config.toml").read_text()

        # Assert
        self.assertIn("\n# quota_window_hours = 5\n", content)

    def test_should_create_neither_the_state_root_nor_the_cache_root(self):
        # Act
        init(self.no_option, self.runtime)

        # Assert
        self.assertEqual(self.runtime.paths.state_root.exists(), False)
        self.assertEqual(self.runtime.paths.cache_root.exists(), False)

    def test_should_rewrite_nothing_on_a_second_run(self):
        # Arrange
        init(self.no_option, self.runtime)
        (self.config_root / ".git").mkdir()
        schema_written_at = (self.config_root / "_schema.awawa").stat().st_mtime_ns
        gitignore_written_at = (self.config_root / ".gitignore").stat().st_mtime_ns
        configuration_written_at = (self.config_root / "config.toml").stat().st_mtime_ns

        # Act
        init(self.no_option, self.runtime)

        # Assert
        self.assertEqual((self.config_root / "_schema.awawa").stat().st_mtime_ns, schema_written_at)
        self.assertEqual((self.config_root / ".gitignore").stat().st_mtime_ns, gitignore_written_at)
        self.assertEqual((self.config_root / "config.toml").stat().st_mtime_ns, configuration_written_at)

    def test_should_create_the_schema_again_and_commit_it_alone(self):
        # Arrange
        init(self.no_option, self.runtime)
        (self.config_root / ".git").mkdir()
        (self.config_root / "_schema.awawa").unlink()
        self.runner.argvs.clear()

        # Act
        document = init(self.no_option, self.runtime)

        # Assert
        self.assertEqual(
            document["items"][1],
            {"name": "schema", "path": str(self.config_root / "_schema.awawa"), "state": "created"},
        )
        self.assertIn(("git", "add", "--", "_schema.awawa"), self.runner.argvs)

    def test_should_leave_the_file_as_it_is_and_report_it_differing(self):
        # Arrange
        init(self.no_option, self.runtime)
        (self.config_root / ".git").mkdir()
        rows = [
            ("schema", "_schema.awawa", 1),
            (".gitignore", ".gitignore", 2),
            ("config.toml", "config.toml", 3),
        ]
        for name, file_name, entry in rows:
            with self.subTest(name=name):
                # Arrange
                edited_file = self.config_root / file_name
                edited_file.write_text("# edited by the user\n")

                # Act
                document = init(self.no_option, self.runtime)

                # Assert
                self.assertEqual(document["items"][entry], {"name": name, "path": str(edited_file), "state": "differs"})
                self.assertEqual(edited_file.read_text(), "# edited by the user\n")

    def test_should_refuse_a_directory_standing_for_a_file_of_the_corpus(self):
        # Arrange
        init(self.no_option, self.runtime)
        (self.config_root / ".git").mkdir()
        (self.config_root / "config.toml").unlink()
        (self.config_root / "config.toml").mkdir()

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            init(self.no_option, self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.config_root / 'config.toml'}: Is a directory")

    def test_should_report_present_and_commit_nothing_on_a_second_run(self):
        # Arrange
        init(self.no_option, self.runtime)
        (self.config_root / ".git").mkdir()
        self.runner.argvs.clear()

        # Act
        document = init(self.no_option, self.runtime)

        # Assert
        self.assertEqual(
            document["items"],
            [
                {"name": "repository", "path": str(self.config_root), "state": "present"},
                {"name": "schema", "path": str(self.config_root / "_schema.awawa"), "state": "present"},
                {"name": ".gitignore", "path": str(self.config_root / ".gitignore"), "state": "present"},
                {"name": "config.toml", "path": str(self.config_root / "config.toml"), "state": "present"},
            ],
        )
        self.assertEqual(
            self.runner.argvs, [("git", "config", "--get", "user.name"), ("git", "config", "--get", "user.email")]
        )

    def test_should_leave_a_file_that_differs_from_the_shipped_one(self):
        # Arrange
        (self.config_root / ".git").mkdir(parents=True)
        (self.config_root / ".gitignore").write_text("*.log\n")

        # Act
        document = init(self.no_option, self.runtime)

        # Assert
        self.assertEqual(
            document["items"][2],
            {"name": ".gitignore", "path": str(self.config_root / ".gitignore"), "state": "differs"},
        )

    def test_should_refuse_a_file_it_cannot_write(self):
        # Arrange
        (self.config_root / ".git").mkdir(parents=True)
        missing_directory = Path(self.root.name) / "missing"
        (self.config_root / "_schema.awawa").symlink_to(missing_directory / "schema")

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            init(self.no_option, self.runtime)

        # Assert
        self.assertEqual(
            str(refusal.exception), f"cannot write {self.config_root / '_schema.awawa'}: No such file or directory"
        )


class InitOverAFileWhereTheRepositoryGoesTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.blocking_file = Path(self.root.name) / "machine"
        self.blocking_file.write_text("")
        runner = ScriptedProcessRunner(
            _create_git_answers(ProcessAnswer(stdout="Ada\n"), ProcessAnswer(stdout="ada@example.org\n"))
        )
        self.runtime = create_test_runtime(create_test_paths(self.blocking_file), run_process=runner.run)

    def test_should_refuse_the_directory_it_cannot_create(self):
        # Arrange
        no_option = argparse.Namespace()

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            init(no_option, self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.blocking_file / 'config'}: Not a directory")


class InitWithoutAGitIdentityTest(unittest.TestCase):
    def test_should_name_the_keys_the_identity_lacks(self):
        # Arrange
        absent = ProcessAnswer(exit_code=1)
        rows = [
            (absent, ProcessAnswer(stdout="ada@example.org\n"), "user.name"),
            (ProcessAnswer(stdout="Ada\n"), absent, "user.email"),
            (absent, absent, "user.name and user.email"),
        ]
        for name, email, lacking in rows:
            with self.subTest(lacking=lacking), tempfile.TemporaryDirectory() as root:
                runtime = create_test_runtime(
                    create_test_paths(Path(root)),
                    run_process=ScriptedProcessRunner(_create_git_answers(name, email)).run,
                )

                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    init(argparse.Namespace(), runtime)

                # Assert
                self.assertEqual(
                    str(refusal.exception), f"the git identity lacks {lacking}; set it with git config --global"
                )
                self.assertEqual(runtime.paths.config_root.exists(), False)


class InitRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(json=True)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(json=True))


class InitExitCodeTest(unittest.TestCase):
    def test_should_exit_0_even_when_a_file_differs(self):
        # Arrange
        document = {"items": [{"name": ".gitignore", "path": "/c/.gitignore", "state": "differs"}]}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class InitTextTest(unittest.TestCase):
    def test_should_print_each_item_the_counts_and_a_warning_per_file_that_differs(self):
        # Arrange
        document = {
            "items": [
                {"name": "repository", "path": "/c", "state": "present"},
                {"name": "schema", "path": "/c/_schema.awawa", "state": "created"},
                {"name": ".gitignore", "path": "/c/.gitignore", "state": "differs"},
            ]
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "present  repository   /c\n"
            "created  schema       /c/_schema.awawa\n"
            "differs  .gitignore   /c/.gitignore\n"
            "\n"
            "init: created 1 · present 1 · differs 1\n"
            "warning: .gitignore differs from the shipped file and is left as it is",
        )
