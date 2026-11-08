import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.corpus.shipped_data import SHIPPED_PROJECT_SCHEMA
from brigade.errors import BrigadeError, CorpusLintFailed
from brigade.registry.install_project_corpus import CorpusInstallation, install_project_corpus
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

BRANCH = "brigade/init-corpus"
SUBJECT = "docs(corpus): install the schema of the project corpus"
LOGIN_ENVIRONMENT = {"GH_TOKEN": "octo-cli"}
LINT_REFUSAL = ProcessAnswer(stdout="L002 refused", exit_code=1)


class _RecordingForgeDouble:
    def __init__(self):
        self.requests = []

    def open_pull_request(self, request: dict, runtime) -> dict:
        self.requests.append(request)
        return {"number": 12}


class InstallProjectCorpusTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.answers = {
            ("git", "rev-parse", "--verify"): ProcessAnswer(exit_code=1),
            ("git", "fetch"): ProcessAnswer(),
            ("git", "worktree"): ProcessAnswer(),
            ("git", "switch"): ProcessAnswer(),
            ("git", "add"): ProcessAnswer(),
            ("git", "diff"): ProcessAnswer(exit_code=1),
            ("git", "commit"): ProcessAnswer(),
            ("git", "push"): ProcessAnswer(),
            ("awawa", "fmt"): ProcessAnswer(),
            ("awawa", "lint"): ProcessAnswer(),
        }
        self.processes = ScriptedProcessRunner(self.answers)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes.run)
        self.worktree = self.runtime.paths.cache_root / "corpus-installs" / "app"

    def _install(self, forge_name: str, forge: object = None) -> dict:
        project = Entity(
            name="app",
            fields=(
                EntityField(name="PATH", value="/srv/app"),
                EntityField(name="MAIN", value="trunk"),
                EntityField(name="CORPUS", value="specs/corpus"),
                EntityField(name="FORGE", value=forge_name),
            ),
        )
        return install_project_corpus(
            self.runtime,
            CorpusInstallation(project=project, forge=forge, read_environment=lambda key: LOGIN_ENVIRONMENT),
        )


class InstallProjectCorpusWithoutAForgeTest(InstallProjectCorpusTestCase):
    def test_should_write_the_template_in_the_corpus_folder(self):
        # Act
        self._install("none")

        # Assert
        self.assertEqual(
            (self.worktree / "specs" / "corpus" / "_schema.awawa").read_text(), SHIPPED_PROJECT_SCHEMA.read_text()
        )

    def test_should_commit_it_on_a_branch_cut_from_the_main_branch(self):
        # Act
        self._install("none")

        # Assert
        self.assertIn(
            ("git", "worktree", "add", "--quiet", "--detach", str(self.worktree), "trunk"), self.processes.argvs
        )
        self.assertIn(("git", "commit", "--quiet", "-m", SUBJECT), self.processes.argvs)
        self.assertIn(("git", "switch", "--quiet", "--create", BRANCH), self.processes.argvs)

    def test_should_leave_no_worktree_behind(self):
        # Act
        self._install("none")

        # Assert
        self.assertEqual(self.processes.argvs[-1], ("git", "worktree", "remove", "--force", str(self.worktree)))

    def test_should_name_the_branch_and_the_merge_command(self):
        # Act
        installed = self._install("none")

        # Assert
        self.assertEqual(
            installed,
            {"branch": BRANCH, "pull_request": None, "merge_command": f"git -C /srv/app merge {BRANCH}"},
        )

    def test_should_refuse_a_branch_that_already_exists(self):
        # Arrange
        self.answers["git", "rev-parse", "--verify"] = ProcessAnswer()
        del self.answers["git", "worktree"]

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            self._install("none")

        # Assert
        self.assertEqual(
            str(refusal.exception), f"the branch {BRANCH} already exists in /srv/app; merge it or delete it"
        )

    def test_should_remove_the_worktree_of_a_template_the_lint_refuses(self):
        # Arrange
        self.answers["awawa", "lint"] = LINT_REFUSAL
        self.answers["git", "ls-tree"] = ProcessAnswer()
        self.answers["git", "rm"] = ProcessAnswer()
        self.answers["git", "clean"] = ProcessAnswer()

        # Act
        with self.assertRaises(CorpusLintFailed):
            self._install("none")

        # Assert
        self.assertEqual(self.processes.argvs[-1], ("git", "worktree", "remove", "--force", str(self.worktree)))


class InstallProjectCorpusOnAForgeTest(InstallProjectCorpusTestCase):
    def test_should_cut_the_branch_from_the_main_branch_of_the_forge(self):
        # Act
        self._install("github", _RecordingForgeDouble())

        # Assert
        self.assertIn(
            ("git", "worktree", "add", "--quiet", "--detach", str(self.worktree), "origin/trunk"), self.processes.argvs
        )

    def test_should_push_the_branch(self):
        # Act
        self._install("github", _RecordingForgeDouble())

        # Assert
        self.assertIn(("git", "push", "--quiet", "origin", BRANCH), self.processes.argvs)

    def test_should_open_a_pull_request_into_the_main_branch(self):
        # Arrange
        forge = _RecordingForgeDouble()

        # Act
        self._install("github", forge)

        # Assert
        self.assertEqual(
            forge.requests,
            [
                {
                    "repository": "/srv/app",
                    "base": "trunk",
                    "branch": BRANCH,
                    "title": SUBJECT,
                    "body": "The awawa schema brigade needs to plan and deliver the tasks of this project.",
                    "milestone": None,
                    "environment": LOGIN_ENVIRONMENT,
                }
            ],
        )

    def test_should_name_the_branch_and_the_pull_request(self):
        # Act
        installed = self._install("github", _RecordingForgeDouble())

        # Assert
        self.assertEqual(installed, {"branch": BRANCH, "pull_request": 12, "merge_command": None})
