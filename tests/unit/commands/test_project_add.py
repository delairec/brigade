import argparse
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.project_add import COMMAND, project_add
from brigade.errors import BrigadeError, UsageError
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner

NO_PROJECT = json.dumps({"entities": []})
APP_PROJECT = json.dumps({"entities": [{"type": "PROJECT", "name": "app"}]})
ELSEWHERE = json.dumps({"fields": [{"name": "PATH", "atoms": ['"/srv/elsewhere"']}]})
LIB_AND_APP = (
    'PROJECT lib\n\tPATH "/srv/lib"\n\tSTATUS active\n\nPROJECT app\n\tPATH "/srv/elsewhere"\n\tSTATUS active\n'
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


def _create_request(path: Path, **options) -> argparse.Namespace:
    return argparse.Namespace(
        path=str(path),
        name=options.get("name"),
        acceptance=["python3 -m unittest"],
        heavy=[],
        setup=[],
        force=options.get("force", False),
        init_corpus=options.get("init_corpus", False),
        corpus=options.get("corpus"),
        corpus_mode=options.get("corpus_mode"),
    )


class _ForgeOpeningPullRequest12Double:
    def open_pull_request(self, request: dict, runtime) -> dict:
        return {"number": 12}


class ProjectAddTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name).resolve()
        self.repository = root / "app"
        self.repository.mkdir()
        self.answers = {
            ("git", "rev-parse", "--git-dir"): ProcessAnswer(stdout=".git\n"),
            ("git", "symbolic-ref"): ProcessAnswer(stdout="origin/main\n"),
            ("git", "remote", "get-url"): ProcessAnswer(stdout="git@github.com:acme/app.git\n"),
            ("git", "ls-files"): ProcessAnswer(stdout="corpus/tasks.awawa\0corpus/decisions.awawa\0"),
            ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=NO_PROJECT),
            ("awawa", "fmt"): ProcessAnswer(),
            ("awawa", "lint"): ProcessAnswer(),
            ("git", "add"): ProcessAnswer(),
            ("git", "diff"): ProcessAnswer(exit_code=1),
            ("git", "commit"): ProcessAnswer(),
        }
        self.runtime = create_test_runtime(create_test_paths(root), run_process=ScriptedProcessRunner(self.answers).run)
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.schema_file.write_text("SCHEMA PROJECT\n")
        self.registry = self.runtime.paths.config_root / "projects.awawa"

    def test_should_register_the_repository_with_what_it_discovered(self):
        # Arrange
        request = _create_request(self.repository, corpus_mode="control")

        # Act
        document = project_add(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "action": "added",
                "project": {
                    "name": "app",
                    "fields": [
                        {"name": "PATH", "value": str(self.repository), "guessed": False},
                        {"name": "REMOTE", "value": "acme/app", "guessed": False},
                        {"name": "MAIN", "value": "main", "guessed": False},
                        {"name": "CORPUS", "value": "corpus", "guessed": False},
                        {"name": "ACCEPTANCE", "value": "python3 -m unittest", "guessed": False},
                        {"name": "FORGE", "value": "github", "guessed": False},
                        {"name": "STATUS", "value": "active", "guessed": False},
                    ],
                },
                "configurations": [],
                "installed_corpus": None,
            },
        )

    def test_should_write_the_project_entity_in_the_registry(self):
        # Arrange
        request = _create_request(self.repository, name="tidepool", corpus_mode="control")

        # Act
        project_add(request, self.runtime)

        # Assert
        self.assertEqual(
            self.registry.read_text(),
            f'PROJECT tidepool\n\tPATH "{self.repository}"\n\tREMOTE "acme/app"\n\tMAIN "main"\n\tCORPUS "corpus"\n'
            '\tACCEPTANCE "python3 -m unittest"\n\tFORGE "github"\n\tSTATUS active\n',
        )

    def test_should_replace_the_project_of_the_same_name_when_forced(self):
        # Arrange
        self.answers["awawa", "status", "PROJECT"] = ProcessAnswer(stdout=APP_PROJECT)
        self.answers["awawa", "show", "@PROJECT.app"] = ProcessAnswer(stdout=ELSEWHERE)
        self.registry.write_text(LIB_AND_APP)
        request = _create_request(self.repository, force=True, corpus_mode="control")

        # Act
        document = project_add(request, self.runtime)

        # Assert
        self.assertEqual(document["action"], "replaced")
        self.assertEqual(
            self.registry.read_text(),
            f'PROJECT lib\n\tPATH "/srv/lib"\n\tSTATUS active\n\nPROJECT app\n\tPATH "{self.repository}"\n'
            '\tREMOTE "acme/app"\n\tMAIN "main"\n\tCORPUS "corpus"\n\tACCEPTANCE "python3 -m unittest"\n'
            '\tFORGE "github"\n\tSTATUS active\n',
        )

    def test_should_refuse_a_name_already_registered_unless_forced(self):
        # Arrange
        self.answers["awawa", "status", "PROJECT"] = ProcessAnswer(stdout=APP_PROJECT)
        self.answers["awawa", "show", "@PROJECT.app"] = ProcessAnswer(stdout=ELSEWHERE)
        request = _create_request(self.repository, corpus_mode="control")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            project_add(request, self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), "@PROJECT.app is already registered; --force replaces it")

    def test_should_refuse_a_path_already_registered_unless_forced(self):
        # Arrange
        self.answers["awawa", "status", "PROJECT"] = ProcessAnswer(
            stdout=json.dumps({"entities": [{"type": "PROJECT", "name": "old"}]})
        )
        self.answers["awawa", "show", "@PROJECT.old"] = ProcessAnswer(
            stdout=json.dumps({"fields": [{"name": "PATH", "atoms": [json.dumps(str(self.repository))]}]})
        )
        request = _create_request(self.repository, corpus_mode="control")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            project_add(request, self.runtime)

        # Assert
        self.assertEqual(
            str(refusal.exception), f"{self.repository} is already registered as @PROJECT.old; --force replaces it"
        )

    def test_should_refuse_a_name_that_is_not_an_identifier(self):
        # Arrange
        request = _create_request(self.repository, name="my app", corpus_mode="control")

        # Act
        with self.assertRaises(UsageError) as refusal:
            project_add(request, self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), "--name my app is not an identifier: letters, digits and _ only")

    def test_should_refuse_a_path_that_is_not_a_git_repository(self):
        # Arrange
        absent = self.repository.parent / "absent"
        request = _create_request(absent, corpus_mode="control")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            project_add(request, self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), f"{absent} is not a git repository")

    def test_should_guess_the_commands_no_flag_gives_and_take_the_others_as_given(self):
        # Arrange
        (self.repository / "package.json").write_text('{"scripts": {"test": "vitest", "lint": "eslint ."}}')
        (self.repository / "package-lock.json").write_text("{}")
        no_acceptance_given = []
        request = argparse.Namespace(
            path=str(self.repository),
            name=None,
            acceptance=no_acceptance_given,
            heavy=["make e2e"],
            setup=["make deps", "make tools"],
            force=False,
            init_corpus=False,
            corpus=None,
            corpus_mode="control",
        )

        # Act
        document = project_add(request, self.runtime)

        # Assert
        self.assertEqual(
            document["project"]["fields"][4:9],
            [
                {"name": "ACCEPTANCE", "value": "npm run test", "guessed": True},
                {"name": "ACCEPTANCE", "value": "npm run lint", "guessed": True},
                {"name": "HEAVY", "value": "make e2e", "guessed": False},
                {"name": "SETUP", "value": "make deps", "guessed": False},
                {"name": "SETUP", "value": "make tools", "guessed": False},
            ],
        )


class ProjectAddRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(path=".", force=False)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(path=".", force=False))


class ProjectAddExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_project_is_registered(self):
        # Arrange
        document = {"action": "added"}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class ProjectAddTextTest(unittest.TestCase):
    def test_should_mark_the_guessed_fields_and_say_no_configuration_was_found(self):
        # Arrange
        document = {
            "action": "added",
            "project": {
                "name": "app",
                "fields": [
                    {"name": "PATH", "value": "/srv/app", "guessed": False},
                    {"name": "ACCEPTANCE", "value": "make test", "guessed": True},
                ],
            },
            "configurations": [],
            "installed_corpus": None,
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "added @PROJECT.app\nPATH        /srv/app\nACCEPTANCE  make test  (guessed)\n"
            "no supported configuration was found",
        )

    def test_should_say_nothing_more_when_a_configuration_was_found(self):
        # Arrange
        document = {
            "action": "replaced",
            "project": {"name": "app", "fields": [{"name": "PATH", "value": "/srv/app", "guessed": False}]},
            "configurations": ["Makefile"],
            "installed_corpus": None,
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "replaced @PROJECT.app\nPATH        /srv/app")


class ProjectAddInstalledCorpusTextTest(unittest.TestCase):
    def test_should_print_the_branch_and_what_delivers_it(self):
        for delivery, expected in [
            ({"pull_request": 12, "merge_command": None}, "pull request #12"),
            ({"pull_request": None, "merge_command": "git -C /srv/app merge corpus"}, "git -C /srv/app merge corpus"),
        ]:
            with self.subTest(expected=expected):
                # Arrange
                document = {
                    "action": "added",
                    "project": {"name": "app", "fields": []},
                    "configurations": ["Makefile"],
                    "installed_corpus": {"branch": "corpus", **delivery},
                }

                # Act
                text = COMMAND.render_text(document)

                # Assert
                self.assertEqual(text, f"added @PROJECT.app\nbranch corpus\n{expected}")


class ProjectAddInitCorpusTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name).resolve()
        self.repository = root / "app"
        self.repository.mkdir()
        self.answers = {
            ("git", "rev-parse", "--git-dir"): ProcessAnswer(stdout=".git\n"),
            ("git", "rev-parse", "--verify"): ProcessAnswer(exit_code=1),
            ("git", "symbolic-ref"): ProcessAnswer(stdout="origin/main\n"),
            ("git", "remote", "get-url"): ProcessAnswer(stdout="https://git.example.org/acme/app.git\n"),
            ("git", "ls-files"): ProcessAnswer(),
            ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=NO_PROJECT),
            ("awawa", "fmt"): ProcessAnswer(),
            ("awawa", "lint"): ProcessAnswer(),
            ("git", "worktree"): ProcessAnswer(),
            ("git", "switch"): ProcessAnswer(),
            ("git", "fetch"): ProcessAnswer(),
            ("git", "push"): ProcessAnswer(),
            ("git", "add"): ProcessAnswer(),
            ("git", "diff"): ProcessAnswer(exit_code=1),
            ("git", "commit"): ProcessAnswer(),
        }
        self.forge = _ForgeOpeningPullRequest12Double()
        self.paths = create_test_paths(root)
        self.runtime = create_test_runtime(
            self.paths,
            run_process=ScriptedProcessRunner(self.answers).run,
            resolve_plugin=lambda kind, name, **places: self.forge,
        )
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.schema_file.write_text("SCHEMA PROJECT\n")
        self.runtime.paths.configuration_file.write_text("")
        self.registry = self.runtime.paths.config_root / "projects.awawa"

    def test_should_register_the_folder_of_the_corpus_it_installed(self):
        # Arrange
        request = _create_request(self.repository, init_corpus=True)

        # Act
        project_add(request, self.runtime)

        # Assert
        self.assertEqual(
            self.registry.read_text(),
            f'PROJECT app\n\tPATH "{self.repository}"\n\tREMOTE "acme/app"\n\tMAIN "main"\n\tCORPUS "corpus"\n'
            '\tACCEPTANCE "python3 -m unittest"\n\tFORGE "none"\n\tSTATUS active\n',
        )

    def test_should_report_the_branch_and_the_merge_command_on_no_forge(self):
        # Arrange
        request = _create_request(self.repository, init_corpus=True)

        # Act
        document = project_add(request, self.runtime)

        # Assert
        self.assertEqual(
            document["installed_corpus"],
            {
                "branch": "brigade/init-corpus",
                "pull_request": None,
                "merge_command": f"git -C {self.repository} merge brigade/init-corpus",
            },
        )

    def test_should_report_the_pull_request_opened_on_the_forge(self):
        # Arrange
        self.answers["git", "remote", "get-url"] = ProcessAnswer(stdout="https://github.com/acme/app.git\n")
        request = _create_request(self.repository, init_corpus=True)

        # Act
        document = project_add(request, self.runtime)

        # Assert
        self.assertEqual(
            document["installed_corpus"],
            {"branch": "brigade/init-corpus", "pull_request": 12, "merge_command": None},
        )

    def test_should_write_the_corpus_in_the_folder_named(self):
        for given, registered in [("docs/spec/", "docs/spec"), (".", ".")]:
            with self.subTest(given=given):
                # Arrange
                request = _create_request(self.repository, init_corpus=True, corpus=given, force=True)

                # Act
                document = project_add(request, self.runtime)

                # Assert
                self.assertEqual(
                    document["project"]["fields"][3], {"name": "CORPUS", "value": registered, "guessed": False}
                )
                schema = self.paths.cache_root / "corpus-installs" / "app" / registered / "_schema.awawa"
                self.assertTrue(schema.is_file(), schema)

    def test_should_refuse_a_repository_already_tracking_a_corpus_file(self):
        # Arrange
        self.answers["git", "ls-files"] = ProcessAnswer(stdout="specs/tasks.awawa\0specs/_schema.awawa\0")
        del self.answers["git", "worktree"]
        request = _create_request(self.repository, init_corpus=True)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            project_add(request, self.runtime)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            f"{self.repository} already tracks specs/tasks.awawa; --init-corpus would add a second corpus",
        )

    def test_should_refuse_a_project_already_registered_before_writing_a_branch(self):
        # Arrange
        self.answers["awawa", "status", "PROJECT"] = ProcessAnswer(stdout=APP_PROJECT)
        self.answers["awawa", "show", "@PROJECT.app"] = ProcessAnswer(stdout=ELSEWHERE)
        del self.answers["git", "worktree"]
        request = _create_request(self.repository, init_corpus=True)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            project_add(request, self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), "@PROJECT.app is already registered; --force replaces it")

    def test_should_refuse_a_corpus_folder_outside_the_repository(self):
        for folder in ["/srv/specs", "../specs", ".."]:
            with self.subTest(folder=folder):
                # Arrange
                request = _create_request(self.repository, init_corpus=True, corpus=folder)

                # Act
                with self.assertRaises(UsageError) as refusal:
                    project_add(request, self.runtime)

                # Assert
                self.assertEqual(str(refusal.exception), f"--corpus {folder} is not a folder inside the repository")

    def test_should_refuse_a_corpus_folder_without_the_installation(self):
        # Arrange
        request = _create_request(self.repository, corpus="specs")

        # Act
        with self.assertRaises(UsageError) as refusal:
            project_add(request, self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), "--corpus names the folder of --init-corpus and needs it")


class _TerminalDouble:
    def __init__(self, *answers: str):
        self.answers = list(answers)
        self.questions = []

    def ask(self, question: str) -> str:
        self.questions.append(question)
        return self.answers.pop(0)


class ProjectAddOnATrackedCorpusTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name).resolve()
        self.repository = root / "app"
        self.repository.mkdir()
        self.answers = {
            ("git", "rev-parse", "--git-dir"): ProcessAnswer(stdout=".git\n"),
            ("git", "rev-parse", "--verify"): ProcessAnswer(exit_code=1),
            ("git", "symbolic-ref"): ProcessAnswer(stdout="origin/main\n"),
            ("git", "remote", "get-url"): ProcessAnswer(stdout="https://git.example.org/acme/app.git\n"),
            ("git", "ls-files"): ProcessAnswer(stdout="specs/tasks.awawa\0specs/rules.awawa\0"),
            ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=NO_PROJECT),
            ("awawa", "fmt"): ProcessAnswer(),
            ("awawa", "lint"): ProcessAnswer(),
            ("git", "worktree"): ProcessAnswer(),
            ("git", "switch"): ProcessAnswer(),
            ("git", "fetch"): ProcessAnswer(),
            ("git", "add"): ProcessAnswer(),
            ("git", "diff"): ProcessAnswer(exit_code=1),
            ("git", "commit"): ProcessAnswer(),
        }
        self.root = root

    def add(self, terminal=None, **options) -> dict:
        request = _create_request(self.repository, **options)
        arguments = {} if terminal is None else {"ask_on_terminal": terminal.ask}
        runtime = create_test_runtime(
            create_test_paths(self.root), run_process=ScriptedProcessRunner(self.answers).run, **arguments
        )
        runtime.paths.config_root.mkdir(parents=True, exist_ok=True)
        runtime.paths.schema_file.write_text("SCHEMA PROJECT\n")
        runtime.paths.configuration_file.write_text("")
        return project_add(request, runtime)

    def assert_registered_field(self, document: dict, name: str, value: str) -> None:
        self.assertIn({"name": name, "value": value, "guessed": False}, document["project"]["fields"])

    def test_should_exit_2_naming_the_option_when_no_terminal_can_answer(self):
        # Arrange
        no_terminal = None

        # Act
        with self.assertRaises(UsageError) as refusal:
            self.add(no_terminal)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            f"{self.repository} tracks specs/tasks.awawa: --corpus-mode control|area says how brigade uses it",
        )

    def test_should_keep_the_corpus_of_the_project_in_control_when_the_option_says_so(self):
        # Act
        document = self.add(corpus_mode="control")

        # Assert
        self.assert_registered_field(document, "CORPUS", "specs")
        self.assertNotIn({"name": "MODE", "value": "control", "guessed": False}, document["project"]["fields"])
        self.assertIsNone(document["installed_corpus"])

    def test_should_confine_brigade_to_its_own_folder_when_the_option_says_area(self):
        # Act
        document = self.add(corpus_mode="area")

        # Assert
        self.assert_registered_field(document, "CORPUS", "brigade")
        self.assert_registered_field(document, "MODE", "area")

    def test_should_take_the_folder_of_the_corpus_option_over_the_default(self):
        for mode, expected in [("control", "docs/spec"), ("area", "docs/spec")]:
            with self.subTest(mode=mode):
                # Act
                document = self.add(corpus_mode=mode, corpus="docs/spec")

                # Assert
                self.assert_registered_field(document, "CORPUS", expected)

    def test_should_ask_the_mode_then_the_folder_on_a_terminal(self):
        # Arrange
        terminal = _TerminalDouble("area", "atelier")

        # Act
        document = self.add(terminal)

        # Assert
        self.assertEqual(terminal.questions, ["Corpus mode, control or area: ", "Corpus folder [brigade]: "])
        self.assert_registered_field(document, "CORPUS", "atelier")

    def test_should_keep_the_folder_proposed_when_the_terminal_answer_is_empty(self):
        # Arrange
        terminal = _TerminalDouble("control", "")

        # Act
        document = self.add(terminal)

        # Assert
        self.assertEqual(terminal.questions[1], "Corpus folder [specs]: ")
        self.assert_registered_field(document, "CORPUS", "specs")

    def test_should_not_ask_the_folder_the_corpus_option_names(self):
        # Arrange
        terminal = _TerminalDouble("area")

        # Act
        document = self.add(terminal, corpus="atelier")

        # Assert
        self.assertEqual(terminal.questions, ["Corpus mode, control or area: "])
        self.assert_registered_field(document, "CORPUS", "atelier")

    def test_should_refuse_a_mode_the_terminal_answers_outside_the_two_modes(self):
        # Arrange
        terminal = _TerminalDouble("elsewhere")

        # Act
        with self.assertRaises(UsageError) as refusal:
            self.add(terminal)

        # Assert
        self.assertEqual(str(refusal.exception), "elsewhere is not a corpus mode: --corpus-mode control|area")

    def test_should_install_the_template_in_the_area_on_a_branch(self):
        # Act
        document = self.add(corpus_mode="area")

        # Assert
        self.assertEqual(
            document["installed_corpus"],
            {
                "branch": "brigade/init-corpus",
                "pull_request": None,
                "merge_command": f"git -C {self.repository} merge brigade/init-corpus",
            },
        )

    def test_should_not_install_an_area_already_holding_its_schema(self):
        # Arrange
        self.answers[("git", "ls-files")] = ProcessAnswer(stdout="specs/tasks.awawa\0brigade/_schema.awawa\0")

        # Act
        document = self.add(corpus_mode="area")

        # Assert
        self.assertIsNone(document["installed_corpus"])


class ProjectAddWithoutATrackedCorpusTest(unittest.TestCase):
    def setUp(self):
        ProjectAddInitCorpusTest.setUp(self)

    def test_should_register_the_project_with_no_question_and_no_corpus_mode(self):
        # Act
        document = project_add(_create_request(self.repository), self.runtime)

        # Assert
        self.assertEqual(
            document["project"]["fields"],
            [
                {"name": "PATH", "value": str(self.repository), "guessed": False},
                {"name": "REMOTE", "value": "acme/app", "guessed": False},
                {"name": "MAIN", "value": "main", "guessed": False},
                {"name": "ACCEPTANCE", "value": "python3 -m unittest", "guessed": False},
                {"name": "FORGE", "value": "none", "guessed": False},
                {"name": "STATUS", "value": "active", "guessed": False},
            ],
        )

    def test_should_refuse_a_corpus_mode_with_nothing_tracked_to_apply_it_to(self):
        for options in [{"corpus_mode": "area"}, {"corpus_mode": "control", "init_corpus": True}]:
            with self.subTest(options=options):
                # Act
                with self.assertRaises(UsageError) as refusal:
                    project_add(_create_request(self.repository, **options), self.runtime)

                # Assert
                self.assertEqual(
                    str(refusal.exception), f"--corpus-mode reads a corpus {self.repository} does not track"
                )


class ProjectAddBeforeInitTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(self.root.name)))

    def test_should_refuse_without_the_operational_corpus(self):
        # Arrange
        request = _create_request(Path("/srv/app"))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            project_add(request, self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), "the operational corpus is missing; run brigade init first")
