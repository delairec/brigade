import fcntl
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject

PACKAGE_JSON = '{"scripts": {"build": "tsc", "test": "vitest", "lint": "eslint ."}}'
INVALID_ENTITY = 'PROJECT bad-name\n\tPATH "/srv/bad"\n\tMAIN "main"\n\tSTATUS active\n'
LOCK_WAIT_S = 5


@unittest.skipUnless(shutil.which("awawa"), "awawa is not on PATH")
class ProjectTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(root)
        self.machine.run_init()
        self.projects = root / "projects"
        self.registry = self.machine.corpus / "projects.awawa"

    def tearDown(self):
        self.root.cleanup()

    def create_project(self, directory_name: str) -> TemporaryProject:
        return TemporaryProject(self.projects / directory_name, self.machine.describe_environment())

    def run_project(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "project", *arguments)

    def count_commits(self) -> str:
        return self.machine.read_git("rev-list", "--count", "HEAD")


class BrigadeProjectAddOnAGitHubRepository(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.project = self.create_project("my-app.v2")
        self.project.run_git("remote", "add", "origin", "https://github.com/acme/my-app.git")
        self.project.run_git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
        self.project.write("corpus/_schema.awawa")
        self.project.write("corpus/tasks.awawa")
        self.project.write("package.json", PACKAGE_JSON)
        self.project.write("package-lock.json", "{}")
        self.project.track("corpus/_schema.awawa", "corpus/tasks.awawa")

    def test_should_report_the_discovered_and_guessed_fields_in_the_versioned_document(self):
        # Act
        completed = self.run_project("add", str(self.project.path), "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "action": "added",
                "project": {
                    "name": "my_app_v2",
                    "fields": [
                        {"name": "PATH", "value": str(self.project.path), "guessed": False},
                        {"name": "REMOTE", "value": "acme/my-app", "guessed": False},
                        {"name": "MAIN", "value": "trunk", "guessed": False},
                        {"name": "CORPUS", "value": "corpus", "guessed": False},
                        {"name": "ACCEPTANCE", "value": "npm run test", "guessed": True},
                        {"name": "ACCEPTANCE", "value": "npm run lint", "guessed": True},
                        {"name": "SETUP", "value": "npm ci", "guessed": True},
                        {"name": "FORGE", "value": "github", "guessed": False},
                        {"name": "STATUS", "value": "active", "guessed": False},
                    ],
                },
                "configurations": ["package.json"],
            },
        )

    def test_should_append_the_entity_to_the_registry(self):
        # Act
        self.run_project("add", str(self.project.path))

        # Assert
        self.assertEqual(
            self.registry.read_text(),
            "PROJECT my_app_v2\n"
            f'\tPATH "{self.project.path}"\n'
            '\tREMOTE "acme/my-app"\n'
            '\tMAIN "trunk"\n'
            '\tCORPUS "corpus"\n'
            '\tACCEPTANCE "npm run test"\n'
            '\tACCEPTANCE "npm run lint"\n'
            '\tSETUP "npm ci"\n'
            '\tFORGE "github"\n'
            "\tSTATUS active\n",
        )

    def test_should_commit_the_registry_alone(self):
        # Arrange
        self.run_project("add", str(self.project.path))

        # Act
        commit = self.machine.read_git("log", "-1", "--format=%s", "--name-only")

        # Assert
        self.assertEqual(commit, "brigade project add: my_app_v2\n\nprojects.awawa\n")

    def test_should_leave_a_corpus_that_lints_clean(self):
        # Arrange
        self.run_project("add", str(self.project.path))

        # Act
        completed = subprocess.run(["awawa", "lint", "--strict", str(self.machine.corpus)], capture_output=True, text=True)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_should_print_the_registration_as_text(self):
        # Act
        completed = self.run_project("add", str(self.project.path))

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "added @PROJECT.my_app_v2",
                f"PATH        {self.project.path}",
                "REMOTE      acme/my-app",
                "MAIN        trunk",
                "CORPUS      corpus",
                "ACCEPTANCE  npm run test  (guessed)",
                "ACCEPTANCE  npm run lint  (guessed)",
                "SETUP       npm ci  (guessed)",
                "FORGE       github",
                "STATUS      active",
            ],
        )

    def test_should_write_the_commands_given_by_flags_and_guess_only_the_others(self):
        # Act
        completed = self.run_project(
            "add",
            str(self.project.path),
            "--name",
            "app",
            "--acceptance",
            "make check",
            "--acceptance",
            "make lint",
            "--heavy",
            "make e2e",
            "--json",
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(
            (document["project"]["name"], document["project"]["fields"][4:8]),
            (
                "app",
                [
                    {"name": "ACCEPTANCE", "value": "make check", "guessed": False},
                    {"name": "ACCEPTANCE", "value": "make lint", "guessed": False},
                    {"name": "HEAVY", "value": "make e2e", "guessed": False},
                    {"name": "SETUP", "value": "npm ci", "guessed": True},
                ],
            ),
        )

    def test_should_write_the_setup_commands_given_by_flags(self):
        # Act
        completed = self.run_project("add", str(self.project.path), "--setup", "make deps", "--setup", "make tools", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["project"]["fields"][6:8],
            [
                {"name": "SETUP", "value": "make deps", "guessed": False},
                {"name": "SETUP", "value": "make tools", "guessed": False},
            ],
        )


class BrigadeProjectAddOnALocalRepository(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.project = self.create_project("notes")

    def test_should_register_the_checked_out_branch_without_a_remote_nor_a_forge(self):
        # Act
        completed = self.run_project("add", str(self.project.path), "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "action": "added",
                "project": {
                    "name": "notes",
                    "fields": [
                        {"name": "PATH", "value": str(self.project.path), "guessed": False},
                        {"name": "MAIN", "value": "main", "guessed": False},
                        {"name": "FORGE", "value": "none", "guessed": False},
                        {"name": "STATUS", "value": "active", "guessed": False},
                    ],
                },
                "configurations": [],
            },
        )

    def test_should_say_that_no_supported_configuration_was_found(self):
        # Act
        completed = self.run_project("add", str(self.project.path))

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "added @PROJECT.notes",
                f"PATH        {self.project.path}",
                "MAIN        main",
                "FORGE       none",
                "STATUS      active",
                "no supported configuration was found",
            ],
        )

    def test_should_register_a_corpus_tracked_at_the_root_as_the_current_folder(self):
        # Arrange
        self.project.write("_schema.awawa")
        self.project.write("spec/tasks.awawa")
        self.project.track("_schema.awawa", "spec/tasks.awawa")

        # Act
        completed = self.run_project("add", str(self.project.path), "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["project"]["fields"][2], {"name": "CORPUS", "value": ".", "guessed": False})


class BrigadeProjectAddWhenThePathIsNotARepository(ProjectTestCase):
    def test_should_exit_1_naming_the_path_and_write_nothing(self):
        # Arrange
        plain_directory = self.projects / "plain"
        plain_directory.mkdir(parents=True)

        # Act
        completed = self.run_project("add", str(plain_directory))

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr, self.registry.exists()),
            (1, "", f"brigade project add: {plain_directory} is not a git repository\n", False),
        )


class BrigadeProjectAddWhenNoMainBranchCanBeTold(ProjectTestCase):
    def test_should_exit_1_naming_the_path_and_write_nothing(self):
        # Arrange
        project = self.create_project("detached")
        project.write("README.md", "detached\n")
        project.track("README.md")
        project.run_git("commit", "--quiet", "-m", "first")
        project.run_git("checkout", "--quiet", "--detach")

        # Act
        completed = self.run_project("add", str(project.path))

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr, self.registry.exists()),
            (
                1,
                "",
                f"brigade project add: {project.path} has neither an origin/HEAD nor a branch checked out;"
                " check out its main branch\n",
                False,
            ),
        )


class BrigadeProjectAddWithANameThatIsNotAnIdentifier(ProjectTestCase):
    def test_should_exit_2_and_write_nothing(self):
        # Arrange
        project = self.create_project("app")

        # Act
        completed = self.run_project("add", str(project.path), "--name", "my-app.v2")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr, self.registry.exists()),
            (
                2,
                "",
                "brigade project add: --name my-app.v2 is not an identifier: letters, digits and _ only\n",
                False,
            ),
        )


class BrigadeProjectAddWhenAlreadyRegistered(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.project = self.create_project("app")
        self.run_project("add", str(self.project.path))
        self.registered = self.registry.read_text()

    def test_should_refuse_a_path_already_registered_naming_its_entity(self):
        # Act
        completed = self.run_project("add", str(self.project.path), "--name", "other")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade project add: {self.project.path} is already registered as @PROJECT.app; --force replaces it\n"),
        )
        self.assertEqual((self.registry.read_text(), self.count_commits()), (self.registered, "2\n"))

    def test_should_refuse_a_name_already_registered_naming_its_entity(self):
        # Arrange
        namesake = self.create_project("elsewhere/app")

        # Act
        completed = self.run_project("add", str(namesake.path))

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", "brigade project add: @PROJECT.app is already registered; --force replaces it\n"),
        )
        self.assertEqual((self.registry.read_text(), self.count_commits()), (self.registered, "2\n"))

    def test_should_replace_the_entity_when_forced(self):
        # Act
        completed = self.run_project("add", str(self.project.path), "--acceptance", "make check", "--force", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["action"], "replaced")
        self.assertEqual(
            self.registry.read_text(),
            "PROJECT app\n"
            f'\tPATH "{self.project.path}"\n'
            '\tMAIN "main"\n'
            '\tACCEPTANCE "make check"\n'
            '\tFORGE "none"\n'
            "\tSTATUS active\n",
        )


class BrigadeProjectAddWhenTheCorpusFailsItsLint(ProjectTestCase):
    def test_should_restore_the_corpus_and_exit_1(self):
        # Arrange
        (self.machine.corpus / "broken.awawa").write_text(INVALID_ENTITY)
        self.machine.read_git("add", "broken.awawa")
        self.machine.read_git("commit", "--quiet", "-m", "a broken entity")
        project = self.create_project("app")

        # Act
        completed = self.run_project("add", str(project.path))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            completed.stderr.startswith("brigade project add: awawa lint --strict refused the change; the corpus is restored\n"),
            completed.stderr,
        )
        self.assertEqual(
            (self.registry.exists(), self.count_commits(), self.machine.read_git("status", "--porcelain")),
            (False, "2\n", ""),
        )


class BrigadeProjectList(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.beta = self.create_project("beta")
        self.alpha = self.create_project("alpha")

    def test_should_print_every_project_with_its_name_path_and_status_in_the_versioned_document(self):
        # Arrange
        self.run_project("add", str(self.beta.path))
        self.run_project("add", str(self.alpha.path))
        self.run_project("pause", "beta")

        # Act
        completed = self.run_project("list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "projects": [
                    {"name": "alpha", "path": str(self.alpha.path), "status": "active"},
                    {"name": "beta", "path": str(self.beta.path), "status": "paused"},
                ],
            },
        )

    def test_should_print_every_project_as_text(self):
        # Arrange
        self.run_project("add", str(self.beta.path), "--name", "the_beta")
        self.run_project("add", str(self.alpha.path))

        # Act
        completed = self.run_project("list")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                f"alpha     active  {self.alpha.path}",
                f"the_beta  active  {self.beta.path}",
            ],
        )

    def test_should_say_that_no_project_is_registered(self):
        # Act
        completed = self.run_project("list")

        # Assert
        self.assertEqual((completed.returncode, completed.stdout), (0, "no project registered\n"))


class BrigadeProjectShow(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.project = self.create_project("app")
        self.run_project("add", str(self.project.path), "--heavy", "make e2e")

    def test_should_print_the_fields_of_the_project_in_the_versioned_document(self):
        # Act
        completed = self.run_project("show", "app", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "project": {
                    "name": "app",
                    "fields": [
                        {"name": "PATH", "value": str(self.project.path)},
                        {"name": "MAIN", "value": "main"},
                        {"name": "HEAVY", "value": "make e2e"},
                        {"name": "FORGE", "value": "none"},
                        {"name": "STATUS", "value": "active"},
                    ],
                },
            },
        )

    def test_should_print_the_fields_of_the_project_as_text(self):
        # Act
        completed = self.run_project("show", "app")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "@PROJECT.app",
                f"PATH        {self.project.path}",
                "MAIN        main",
                "HEAVY       make e2e",
                "FORGE       none",
                "STATUS      active",
            ],
        )

    def test_should_exit_1_for_an_unknown_name(self):
        # Act
        completed = self.run_project("show", "ghost")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", "brigade project show: @PROJECT.ghost is not registered\n"),
        )


class BrigadeProjectPauseAndResume(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.project = self.create_project("app")
        self.run_project("add", str(self.project.path))

    def test_should_pause_the_project_and_commit_the_registry(self):
        # Act
        completed = self.run_project("pause", "app", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), {"schema_version": 1, "project": "app", "status": "paused", "changed": True})
        self.assertEqual(self.registry.read_text().splitlines()[-1], "\tSTATUS paused")
        self.assertEqual(self.machine.read_git("log", "-1", "--format=%s", "--name-only"), "brigade project pause: app\n\nprojects.awawa\n")

    def test_should_resume_a_paused_project(self):
        # Arrange
        self.run_project("pause", "app")

        # Act
        completed = self.run_project("resume", "app")

        # Assert
        self.assertEqual((completed.returncode, completed.stdout), (0, "resumed @PROJECT.app\n"))
        self.assertEqual(self.registry.read_text().splitlines()[-1], "\tSTATUS active")

    def test_should_leave_a_project_already_in_that_status_as_it_is(self):
        rows = [
            ("pause", "paused", "@PROJECT.app is already paused\n", "3\n"),
            ("resume", "active", "@PROJECT.app is already active\n", "4\n"),
        ]
        for action, status, text, commits in rows:
            with self.subTest(action=action):
                # Arrange
                self.run_project(action, "app")

                # Act
                completed = self.run_project(action, "app")

                # Assert
                self.assertEqual(
                    (completed.returncode, completed.stdout, self.registry.read_text().splitlines()[-1], self.count_commits()),
                    (0, text, f"\tSTATUS {status}", commits),
                )

    def test_should_exit_1_for_an_unknown_name(self):
        for action in ["pause", "resume"]:
            with self.subTest(action=action):
                # Act
                completed = self.run_project(action, "ghost")

                # Assert
                self.assertEqual(
                    (completed.returncode, completed.stdout, completed.stderr),
                    (1, "", f"brigade project {action}: @PROJECT.ghost is not registered\n"),
                )


class BrigadeProjectWhileTheCorpusIsLocked(ProjectTestCase):
    def test_should_wait_for_the_lock_of_the_corpus_repository(self):
        # Arrange
        project = self.create_project("app")
        self.run_project("add", str(project.path))
        lock_files = list((self.machine.state_home / "brigade" / "locks").iterdir())
        with open(lock_files[0], "a") as held_lock:
            fcntl.flock(held_lock, fcntl.LOCK_EX)

            # Act
            waiting = self.detect_waiting(["project", "pause", "app"])

        # Assert
        self.assertEqual((len(lock_files), waiting, self.registry.read_text().splitlines()[-1]), (1, True, "\tSTATUS active"))

    def detect_waiting(self, arguments: list) -> bool:
        try:
            subprocess.run(
                [sys.executable, str(CLONE_ENTRY_POINT), *arguments],
                capture_output=True,
                env=self.machine.describe_environment(),
                timeout=LOCK_WAIT_S,
            )
        except subprocess.TimeoutExpired:
            return True
        return False


class BrigadeProjectBeforeInit(unittest.TestCase):
    def test_should_exit_1_naming_brigade_init(self):
        rows = [
            ("add", ("add", "/srv/app")),
            ("list", ("list",)),
            ("show", ("show", "app")),
            ("pause", ("pause", "app")),
            ("resume", ("resume", "app")),
        ]
        for action, arguments in rows:
            with self.subTest(action=action), tempfile.TemporaryDirectory() as root:
                # Arrange
                machine = TemporaryMachine(Path(root))

                # Act
                completed = machine.run_brigade(CLONE_ENTRY_POINT, "project", *arguments, "--json")

                # Assert
                self.assertEqual(
                    (completed.returncode, completed.stdout, completed.stderr),
                    (1, "", f"brigade project {action}: the operational corpus is missing; run brigade init first\n"),
                )
