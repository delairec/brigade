import sys
import tempfile
import unittest
from pathlib import Path

from tests.cli.run_while_lock_held import run_while_lock_held
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject

PACKAGE_JSON = '{"scripts": {"build": "tsc", "test": "vitest", "lint": "eslint ."}}'


class ProjectTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(root)
        self.machine.install_awawa(self)
        self.machine.run_init()
        self.projects = root / "projects"
        self.registry = self.machine.corpus / "projects.awawa"

    def tearDown(self):
        self.root.cleanup()

    def create_project(self, directory_name: str) -> TemporaryProject:
        return TemporaryProject(self.projects / directory_name, self.machine.describe_environment())

    def run_project(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "project", *arguments)


class BrigadeProjectAddOnAGitHubRepositoryTest(ProjectTestCase):
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

    def test_should_register_the_project_commit_the_registry_alone_and_print_the_registration(self):
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
        self.assertEqual(completed.stderr, "")
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
        self.assertEqual(
            self.machine.read_git("log", "-1", "--format=%s", "--name-only"),
            "brigade project add: my_app_v2\n\nprojects.awawa\n",
        )


class BrigadeProjectListTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.beta = self.create_project("beta")
        self.alpha = self.create_project("alpha")

    def test_should_print_the_projects_as_a_table_under_its_header(self):
        # Arrange
        self.run_project("add", str(self.beta.path), "--name", "the_beta")
        self.run_project("add", str(self.alpha.path))

        # Act
        completed = self.run_project("list")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "name      status  path",
                f"alpha     active  {self.alpha.path}",
                f"the_beta  active  {self.beta.path}",
            ],
        )


class BrigadeProjectShowTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.project = self.create_project("app")
        self.run_project("add", str(self.project.path), "--heavy", "make e2e")

    def test_should_print_the_fields_of_the_project_as_text(self):
        # Act
        completed = self.run_project("show", "app")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
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


class BrigadeProjectPauseAndResumeTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.project = self.create_project("app")
        self.run_project("add", str(self.project.path))

    def test_should_resume_a_paused_project(self):
        # Arrange
        self.run_project("pause", "app")

        # Act
        completed = self.run_project("resume", "app")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "resumed @PROJECT.app\n")
        self.assertEqual(completed.stderr, "")
        self.assertEqual(
            self.registry.read_text(),
            f'PROJECT app\n\tPATH "{self.project.path}"\n\tMAIN "main"\n\tFORGE "none"\n\tSTATUS active\n',
        )
        self.assertEqual(
            self.machine.read_git("log", "-2", "--format=%s"),
            "brigade project resume: app\nbrigade project pause: app\n",
        )


class BrigadeProjectWhileTheCorpusIsLockedTest(ProjectTestCase):
    def test_should_wait_for_the_lock_of_the_corpus_repository(self):
        # Arrange
        project = self.create_project("app")
        self.run_project("add", str(project.path))
        (lock_file,) = (self.machine.state_home / "brigade" / "locks").iterdir()
        argv = [sys.executable, str(CLONE_ENTRY_POINT), "project", "pause", "app"]

        # Act
        with run_while_lock_held(argv, self.machine.describe_environment(), lock_file) as wait_line:
            registry_while_waiting = self.registry.read_text()

        # Assert
        self.assertEqual(wait_line, f"brigade: waiting for the lock {lock_file}, held by pid 4242\n")
        self.assertEqual(
            registry_while_waiting,
            f'PROJECT app\n\tPATH "{project.path}"\n\tMAIN "main"\n\tFORGE "none"\n\tSTATUS active\n',
        )
