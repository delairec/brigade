import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject

RELAY_EXECUTABLES = Path(__file__).resolve().parent / "fixtures" / "executables" / "awawa-relay"
LOCK_WAIT_S = 5


@unittest.skipUnless(shutil.which("awawa"), "awawa is not on PATH")
class CorpusTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(root)
        self.machine.run_init()
        self.project = TemporaryProject(root / "projects" / "app", self.machine.describe_environment())
        self.project.write("corpus/tasks.awawa", "committed\n")
        self.project.track("corpus/tasks.awawa")
        self.project.run_git("commit", "--quiet", "-m", "first")
        self.sha = self.project.run_git("rev-parse", "HEAD").strip()
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(self.project.path))
        self.refs = self.machine.cache_home / "brigade" / "refs"

    def tearDown(self):
        self.root.cleanup()

    def run_corpus(self, *arguments: str, environment: dict | None = None):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "corpus", *arguments, environment=environment)


class BrigadeCorpusAtABranch(CorpusTestCase):
    def test_should_print_the_document_of_the_extracted_tree(self):
        # Act
        completed = self.run_corpus("app", "--ref", "main", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "project": "app",
                "ref": "main",
                "sha": self.sha,
                "kind": "archive",
                "root": str(self.refs / "app" / self.sha),
            },
        )

    def test_should_print_the_tree_as_text(self):
        # Act
        completed = self.run_corpus("app", "--ref", "main")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "@PROJECT.app",
                "ref   main",
                f"sha   {self.sha}",
                "kind  archive",
                f"root  {self.refs / 'app' / self.sha}",
            ],
        )


class BrigadeCorpusOfAWorktree(CorpusTestCase):
    def test_should_read_the_worktree_of_the_branch_in_place(self):
        # Act
        completed = self.run_corpus("app", "--ref", "worktree:main", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "project": "app",
                "ref": "worktree:main",
                "sha": self.sha,
                "kind": "worktree",
                "root": str(self.project.path),
            },
        )

    def test_should_print_a_worktree_named_by_its_path_with_no_ref(self):
        # Arrange
        detached_tree = self.project.path.parent / "detached-tree"
        self.project.run_git("worktree", "add", "--quiet", "--detach", str(detached_tree), "HEAD")

        # Act
        completed = self.run_corpus("app", "--worktree", str(detached_tree))

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "@PROJECT.app",
                f"sha   {self.sha}",
                "kind  worktree",
                f"root  {detached_tree}",
            ],
        )

    def test_should_refuse_a_ref_and_a_worktree_together(self):
        # Act
        completed = self.run_corpus("app", "--ref", "main", "--worktree", str(self.project.path))

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout),
            (2, ""),
        )


class BrigadeCorpusWithAwawaArguments(CorpusTestCase):
    def test_should_pass_the_output_and_the_exit_code_of_awawa_through_after_the_sha(self):
        # Arrange
        environment = {
            **self.machine.describe_environment(),
            "PATH": f"{RELAY_EXECUTABLES}{os.pathsep}{os.environ['PATH']}",
        }

        # Act
        completed = self.run_corpus("app", "--ref", "main", "--", "lint", "--strict", ".", environment=environment)

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (
                3,
                f"awawa lint --strict . in {self.refs / 'app' / self.sha}\n",
                f"brigade corpus: @PROJECT.app at {self.sha}\nawawa diagnostic\n",
            ),
        )


class BrigadeCorpusUnderACacheBound(CorpusTestCase):
    def test_should_keep_the_cache_under_refs_cache_mb(self):
        # Arrange
        self.machine.write_configuration("refs_cache_mb = 0\n")
        self.project.write("corpus/tasks.awawa", "second\n")
        self.project.run_git("commit", "--quiet", "--all", "-m", "second")
        self.run_corpus("app", "--ref", self.sha)

        # Act
        self.run_corpus("app", "--ref", "main")

        # Assert
        self.assertEqual(os.listdir(self.refs / "app"), [self.project.run_git("rev-parse", "HEAD").strip()])


class BrigadeCorpusWhileTheCacheIsLocked(CorpusTestCase):
    def test_should_wait_for_the_lock_of_the_cache_before_pruning(self):
        # Arrange
        lock_file = self.machine.state_home / "brigade" / "locks" / "refs-cache.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_file, "a") as held_lock:
            fcntl.flock(held_lock, fcntl.LOCK_EX)

            # Act
            waiting = self.detect_waiting(["app", "--ref", "main"])

        # Assert
        self.assertTrue(waiting)

    def test_should_wait_for_the_lock_of_the_cache_before_reading_a_cached_tree(self):
        # Arrange
        self.run_corpus("app", "--ref", "main")
        lock_file = self.machine.state_home / "brigade" / "locks" / "refs-cache.lock"
        with open(lock_file, "a") as held_lock:
            fcntl.flock(held_lock, fcntl.LOCK_EX)

            # Act
            waiting = self.detect_waiting(["app", "--ref", "main"])

        # Assert
        self.assertTrue(waiting)

    def detect_waiting(self, arguments: list) -> bool:
        try:
            subprocess.run(
                [sys.executable, str(CLONE_ENTRY_POINT), "corpus", *arguments],
                capture_output=True,
                env=self.machine.describe_environment(),
                timeout=LOCK_WAIT_S,
            )
        except subprocess.TimeoutExpired:
            return True
        return False


class BrigadeCorpusOnWhatItCannotRead(CorpusTestCase):
    def test_should_exit_1_naming_what_it_cannot_read(self):
        rows = [
            ("an unknown project", ("ghost", "--ref", "main"), "brigade corpus: @PROJECT.ghost is not registered\n"),
            (
                "a ref the repository does not resolve",
                ("app", "--ref", "nowhere"),
                "brigade corpus: the ref nowhere is not a commit of @PROJECT.app\n",
            ),
            (
                "a branch no worktree holds",
                ("app", "--ref", "worktree:ghost"),
                "brigade corpus: no worktree of @PROJECT.app has the branch ghost checked out\n",
            ),
            (
                "a path no worktree holds",
                ("app", "--worktree", "/nowhere/tree"),
                "brigade corpus: no worktree of @PROJECT.app is at /nowhere/tree\n",
            ),
        ]
        for case, arguments, expected_error in rows:
            with self.subTest(case=case):
                # Act
                completed = self.run_corpus(*arguments)

                # Assert
                self.assertEqual((completed.returncode, completed.stdout, completed.stderr), (1, "", expected_error))


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class BrigadeCorpusWhereTheMachineRefusesTheCache(CorpusTestCase):
    def setUp(self):
        super().setUp()
        self.machine.cache_home.mkdir(exist_ok=True)

    def tearDown(self):
        self.machine.cache_home.chmod(0o700)
        super().tearDown()

    def test_should_exit_1_naming_the_cache_directory_it_cannot_create(self):
        # Arrange
        self.machine.cache_home.chmod(0o500)

        # Act
        completed = self.run_corpus("app", "--ref", "main")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade corpus: cannot write {self.machine.cache_home / 'brigade'}: Permission denied\n"),
        )
