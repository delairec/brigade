import argparse
import tempfile
import tomllib
import unittest
from pathlib import Path

from brigade.commands.init import COMMAND, init
from brigade.corpus.shipped_data import SHIPPED_SCHEMA
from brigade.errors import BrigadeError, CannotWrite, ToolNotFound
from tests.unit.client_double import create_built_in_clients
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner, create_corpus_double
from tests.unit.commands.create_plugin_resolver import create_plugin_resolver
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

NOT_INSTALLED = {"schema_version": 1, "installed": False, "unit_files": [], "cron_line": None, "next_activation": None}
TIMER_INSTALLED = {
    "schema_version": 1,
    "installed": True,
    "unit_files": ["/u/brigade.timer"],
    "cron_line": None,
    "next_activation": None,
}
NO_PROJECT = {}
REMOTE_URL = "git@example.org:ada/brigade-config.git"


class SchedulerStatusDouble:
    def __init__(self, status: dict):
        self.status = status

    def read_status(self, request: dict, runtime) -> dict:
        return self.status


def _create_machine_plugins() -> dict:
    return {
        **create_built_in_clients(),
        ("scheduler", "systemd"): SchedulerStatusDouble(NOT_INSTALLED),
        ("scheduler", "cron"): SchedulerStatusDouble(NOT_INSTALLED),
    }


def _create_git_answers(name: ProcessAnswer, email: ProcessAnswer) -> dict:
    return {
        ("git", "config", "--get", "user.name"): name,
        ("git", "config", "--get", "user.email"): email,
        ("git", "init"): ProcessAnswer(),
        ("git", "add"): ProcessAnswer(),
        ("git", "diff"): ProcessAnswer(exit_code=1),
        ("git", "commit"): ProcessAnswer(),
        ("git", "remote", "get-url", "origin"): ProcessAnswer(exit_code=2),
        ("git", "remote", "add"): ProcessAnswer(),
        ("claude", "--version"): ProcessAnswer(stdout="2.1.291\n"),
        ("vibe", "--version"): ToolNotFound("vibe"),
    }


def _create_machine_runtime(root: Path, answers: dict, entities: dict = NO_PROJECT):
    runner = ScriptedProcessRunner(answers, fallback=create_corpus_double(entities))
    runtime = create_test_runtime(
        create_test_paths(root),
        run_process=runner.run,
        resolve_plugin=create_plugin_resolver(_create_machine_plugins()),
    )
    return runtime, runner


class InitTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.answers = _create_git_answers(ProcessAnswer(stdout="Ada\n"), ProcessAnswer(stdout="ada@example.org\n"))
        self.runtime, self.runner = _create_machine_runtime(Path(self.root.name), self.answers)
        self.config_root = self.runtime.paths.config_root
        self.no_option = argparse.Namespace(remote=None)

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
                "clients": ["claude-code"],
                "client": "claude-code",
                "steps": ["brigade doctor", "brigade project add <path>", "brigade scheduler install"],
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
        self.answers[("claude", "--version")] = ToolNotFound("claude")
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
        self.assertNotIn(("git", "add", "--", "_schema.awawa", ".gitignore"), self.runner.argvs)
        self.assertNotIn(("git", "commit", "--quiet", "-m", "brigade init: the operational corpus"), self.runner.argvs)

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
        answers = _create_git_answers(ProcessAnswer(stdout="Ada\n"), ProcessAnswer(stdout="ada@example.org\n"))
        self.runtime, _ = _create_machine_runtime(self.blocking_file, answers)

    def test_should_refuse_the_directory_it_cannot_create(self):
        # Arrange
        no_option = argparse.Namespace(remote=None)

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
                runtime, _ = _create_machine_runtime(Path(root), _create_git_answers(name, email))

                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    init(argparse.Namespace(remote=None), runtime)

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
            ],
            "clients": ["claude-code"],
            "client": "claude-code",
            "steps": ["brigade doctor"],
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
            "warning: .gitignore differs from the shipped file and is left as it is\n"
            "\n"
            "next steps:\n"
            "  brigade doctor",
        )

    def test_should_name_the_clients_found_while_the_configuration_names_none(self):
        # Arrange
        rows = [
            ("none", [], "client: no supported client answers its probe; the client key is left commented"),
            (
                "several",
                ["claude-code", "vibe"],
                "client: claude-code, vibe answer their probe; the client key is left commented",
            ),
        ]
        for case, clients, expected_line in rows:
            with self.subTest(case=case):
                document = {
                    "items": [{"name": "repository", "path": "/c", "state": "present"}],
                    "clients": clients,
                    "client": None,
                    "steps": ["brigade doctor", "set the client key in /c/config.toml"],
                }

                # Act
                text = COMMAND.render_text(document)

                # Assert
                self.assertEqual(
                    text,
                    "present  repository   /c\n"
                    "\n"
                    "init: created 0 · present 1 · differs 0\n"
                    f"{expected_line}\n"
                    "\n"
                    "next steps:\n"
                    "  brigade doctor\n"
                    "  set the client key in /c/config.toml",
                )


class InitClientKeyTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.answers = _create_git_answers(ProcessAnswer(stdout="Ada\n"), ProcessAnswer(stdout="ada@example.org\n"))
        self.runtime, _ = _create_machine_runtime(Path(self.root.name), self.answers)
        self.configuration_file = self.runtime.paths.configuration_file

    def test_should_write_the_client_key_of_the_one_client_answering_its_probe(self):
        # Act
        init(argparse.Namespace(remote=None), self.runtime)

        # Assert
        self.assertEqual(tomllib.loads(self.configuration_file.read_text()), {"client": "claude-code"})

    def test_should_leave_the_client_key_commented_and_name_the_clients_found_when_none_or_several_answer(self):
        # Arrange
        rows = [
            ("none", ToolNotFound("claude"), ToolNotFound("vibe"), []),
            ("several", ProcessAnswer(stdout="2.1.291\n"), ProcessAnswer(stdout="1.0.0\n"), ["claude-code", "vibe"]),
        ]
        for case, claude_answer, vibe_answer, expected_clients in rows:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as root:
                answers = {**self.answers, ("claude", "--version"): claude_answer, ("vibe", "--version"): vibe_answer}
                runtime, _ = _create_machine_runtime(Path(root), answers)

                # Act
                document = init(argparse.Namespace(remote=None), runtime)

                # Assert
                self.assertEqual(tomllib.loads(runtime.paths.configuration_file.read_text()), {})
                self.assertEqual([document["clients"], document["client"]], [expected_clients, None])

    def test_should_name_no_client_in_the_configuration_when_none_answers(self):
        # Arrange
        self.answers[("claude", "--version")] = ToolNotFound("claude")

        # Act
        init(argparse.Namespace(remote=None), self.runtime)

        # Assert
        self.assertNotIn("claude", self.configuration_file.read_text())


class InitStepsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.answers = _create_git_answers(ProcessAnswer(stdout="Ada\n"), ProcessAnswer(stdout="ada@example.org\n"))
        self.answers[("claude", "--version")] = ToolNotFound("claude")
        self.no_option = argparse.Namespace(remote=None)

    def test_should_name_every_step_left_on_a_fresh_machine(self):
        # Arrange
        runtime, _ = _create_machine_runtime(Path(self.root.name), self.answers)

        # Act
        document = init(self.no_option, runtime)

        # Assert
        self.assertEqual(
            document["steps"],
            [
                "brigade doctor",
                f"set the client key in {runtime.paths.configuration_file}",
                "brigade project add <path>",
                "brigade scheduler install",
            ],
        )

    def test_should_drop_the_step_of_a_project_once_one_is_registered(self):
        # Arrange
        registered_project = {"PROJECT": {"shop": [("PATH", "/srv/shop")]}}
        runtime, _ = _create_machine_runtime(Path(self.root.name), self.answers, registered_project)

        # Act
        document = init(self.no_option, runtime)

        # Assert
        self.assertNotIn("brigade project add <path>", document["steps"])

    def test_should_keep_the_step_of_a_project_while_awawa_cannot_list_the_projects(self):
        # Arrange
        self.answers[("awawa",)] = ToolNotFound("awawa")
        runtime, _ = _create_machine_runtime(Path(self.root.name), self.answers)

        # Act
        document = init(self.no_option, runtime)

        # Assert
        self.assertIn("brigade project add <path>", document["steps"])

    def test_should_drop_the_step_of_the_scheduler_once_one_is_installed(self):
        # Arrange
        runtime = create_test_runtime(
            create_test_paths(Path(self.root.name)),
            run_process=ScriptedProcessRunner(self.answers, fallback=create_corpus_double(NO_PROJECT)).run,
            resolve_plugin=create_plugin_resolver(
                {**_create_machine_plugins(), ("scheduler", "systemd"): SchedulerStatusDouble(TIMER_INSTALLED)}
            ),
        )

        # Act
        document = init(self.no_option, runtime)

        # Assert
        self.assertNotIn("brigade scheduler install", document["steps"])

    def test_should_keep_the_step_of_the_client_key_while_the_configuration_is_unreadable(self):
        # Arrange
        runtime, _ = _create_machine_runtime(Path(self.root.name), self.answers)
        runtime.paths.configuration_file.parent.mkdir(parents=True)
        runtime.paths.configuration_file.write_text('client = "vibe\n')

        # Act
        document = init(self.no_option, runtime)

        # Assert
        self.assertIn(f"set the client key in {runtime.paths.configuration_file}", document["steps"])

    def test_should_drop_the_step_of_the_client_key_once_the_configuration_names_a_client(self):
        # Arrange
        runtime, _ = _create_machine_runtime(Path(self.root.name), self.answers)
        runtime.paths.configuration_file.parent.mkdir(parents=True)
        runtime.paths.configuration_file.write_text('client = "vibe"\n')

        # Act
        document = init(self.no_option, runtime)

        # Assert
        self.assertEqual(document["client"], "vibe")


class InitRemoteTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.answers = _create_git_answers(ProcessAnswer(stdout="Ada\n"), ProcessAnswer(stdout="ada@example.org\n"))
        self.runtime, self.runner = _create_machine_runtime(Path(self.root.name), self.answers)
        self.config_root = self.runtime.paths.config_root

    def test_should_set_the_url_as_origin_of_the_configuration_repository(self):
        # Act
        document = init(argparse.Namespace(remote=REMOTE_URL), self.runtime)

        # Assert
        self.assertIn(("git", "remote", "add", "origin", REMOTE_URL), self.runner.argvs)
        self.assertEqual(document["items"][1], {"name": "remote", "path": REMOTE_URL, "state": "created"})

    def test_should_report_present_an_origin_already_at_the_url(self):
        # Arrange
        self.answers[("git", "remote", "get-url", "origin")] = ProcessAnswer(stdout=f"{REMOTE_URL}\n")

        # Act
        document = init(argparse.Namespace(remote=REMOTE_URL), self.runtime)

        # Assert
        self.assertEqual(document["items"][1], {"name": "remote", "path": REMOTE_URL, "state": "present"})
        self.assertNotIn(("git", "remote", "add", "origin", REMOTE_URL), self.runner.argvs)

    def test_should_refuse_to_replace_an_origin_at_another_url(self):
        # Arrange
        self.answers[("git", "remote", "get-url", "origin")] = ProcessAnswer(stdout="git@example.org:ada/old.git\n")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            init(argparse.Namespace(remote=REMOTE_URL), self.runtime)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            f"the origin of {self.config_root} is git@example.org:ada/old.git; "
            f"set it with git -C {self.config_root} remote set-url origin {REMOTE_URL}",
        )

    def test_should_leave_the_repository_local_without_the_option(self):
        # Act
        init(argparse.Namespace(remote=None), self.runtime)

        # Assert
        self.assertNotIn(("git", "remote", "get-url", "origin"), self.runner.argvs)


class InitArgumentsTest(unittest.TestCase):
    def test_should_take_the_remote_of_the_configuration_repository(self):
        # Arrange
        parser = argparse.ArgumentParser()
        for argument in COMMAND.arguments:
            parser.add_argument(*argument.flags, **argument.settings)

        # Act
        options = parser.parse_args(["--remote", REMOTE_URL])

        # Assert
        self.assertEqual(options.remote, REMOTE_URL)
