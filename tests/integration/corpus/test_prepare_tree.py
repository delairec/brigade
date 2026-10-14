import os
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from brigade.corpus.prepare_tree import Tree, TreeRequest, prepare_tree
from brigade.errors import BrigadeError, CannotWrite
from tests.integration.run_process_without_trail import run_process_without_trail
from tests.process_launcher import ProcessLauncher

IDENTITY = ("-c", "user.name=Ada Lovelace", "-c", "user.email=ada@example.org")
FIRST_READ = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)
SECOND_READ = datetime(2026, 10, 6, 10, 0, tzinfo=UTC)
THIRD_READ = datetime(2026, 10, 6, 11, 0, tzinfo=UTC)
FOURTH_READ = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
ROOMY_BOUND_BYTES = 1024 * 1024 * 1024
A_DIRECTORY_OF_ANOTHER_OWNER = Path("/")


def run_git(repository: Path, *arguments: str) -> str:
    completed = ProcessLauncher.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


class PrepareTreeTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.workspace = Path(self.root.name).resolve()
        self.repository = self.workspace / "app"
        self.repository.mkdir()
        self.cache = self.workspace / "cache" / "refs"
        run_git(self.repository, "init", "--quiet", "--initial-branch=main")

    def tearDown(self):
        self.root.cleanup()

    def commit(self, relative_path: str, content: str) -> str:
        file = self.repository / relative_path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content)
        return self.record(relative_path)

    def commit_link(self, relative_path: str, target: str) -> str:
        link = self.repository / relative_path
        link.parent.mkdir(parents=True, exist_ok=True)
        link.unlink(missing_ok=True)
        link.symlink_to(target)
        return self.record(relative_path)

    def record(self, relative_path: str) -> str:
        run_git(self.repository, "add", "--", relative_path)
        run_git(self.repository, *IDENTITY, "commit", "--quiet", "-m", f"write {relative_path}")
        return run_git(self.repository, "rev-parse", "HEAD").strip()

    def create_request(self, **changes) -> TreeRequest:
        request = TreeRequest(
            project="app",
            repository=self.repository,
            ref=None,
            worktree=None,
            cache=self.cache,
            cache_bound_bytes=ROOMY_BOUND_BYTES,
            cache_lock=self.workspace / "locks" / "refs-cache.lock",
            now=FIRST_READ,
        )
        return replace(request, **changes)


class PrepareTreeAtABranchOrAShaTest(PrepareTreeTestCase):
    def setUp(self):
        super().setUp()
        self.commit("src/app.py", "print('app')\n")
        self.sha = self.commit("corpus/tasks.awawa", "committed\n")
        (self.repository / "corpus" / "tasks.awawa").write_text("edited, not committed\n")

    def test_should_extract_the_whole_committed_tree_into_the_cache_of_the_project(self):
        # Act
        tree = prepare_tree(run_process_without_trail, self.create_request(ref="main"))

        # Assert
        root = self.cache / "app" / self.sha
        self.assertEqual(
            (tree, (root / "corpus" / "tasks.awawa").read_text(), (root / "src" / "app.py").read_text()),
            (
                Tree(project="app", ref="main", sha=self.sha, kind="archive", root=root),
                "committed\n",
                "print('app')\n",
            ),
        )

    def test_should_resolve_an_abbreviated_sha_to_the_whole_sha(self):
        # Act
        tree = prepare_tree(run_process_without_trail, self.create_request(ref=self.sha[:7]))

        # Assert
        self.assertEqual(tree.sha, self.sha)

    def test_should_leave_the_tree_alone_in_the_cache_of_the_project(self):
        # Act
        prepare_tree(run_process_without_trail, self.create_request(ref="main"))

        # Assert
        self.assertEqual(list((self.cache / "app").iterdir()), [self.cache / "app" / self.sha])

    def test_should_read_a_tree_already_in_the_cache_without_extracting_it_again(self):
        # Arrange
        prepare_tree(run_process_without_trail, self.create_request(ref="main"))
        (self.cache / "app" / self.sha / "corpus" / "tasks.awawa").write_text("left in the cache\n")

        # Act
        tree = prepare_tree(run_process_without_trail, self.create_request(ref="main", now=SECOND_READ))

        # Assert
        self.assertEqual((tree.root / "corpus" / "tasks.awawa").read_text(), "left in the cache\n")

    def test_should_refuse_a_ref_the_repository_does_not_resolve_naming_it(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            prepare_tree(run_process_without_trail, self.create_request(ref="nowhere"))

        # Assert
        self.assertEqual(str(raised.exception), "the ref nowhere is not a commit of @PROJECT.app")


class PrepareTreeOfACommitHoldingALinkInsideItsTreeTest(PrepareTreeTestCase):
    def setUp(self):
        super().setUp()
        self.commit("src/app.py", "print('app')\n")
        self.commit_link("docs/app.py", "../src/app.py")

    def test_should_extract_the_link_reading_through_it_to_the_file_of_the_tree(self):
        # Act
        tree = prepare_tree(run_process_without_trail, self.create_request(ref="main"))

        # Assert
        self.assertEqual((tree.root / "docs" / "app.py").read_text(), "print('app')\n")


class PrepareTreeOfACommitHoldingALinkOutsideItsTreeTest(PrepareTreeTestCase):
    def test_should_refuse_the_link_naming_the_project_and_the_member(self):
        for target in ["../../../.ssh/id_ed25519", "/home/someone/.ssh/id_ed25519"]:
            with self.subTest(target=target):
                # Arrange
                self.commit_link("corpus/keys", target)

                # Act
                with self.assertRaises(BrigadeError) as raised:
                    prepare_tree(run_process_without_trail, self.create_request(ref="main"))

                # Assert
                self.assertEqual(
                    str(raised.exception),
                    "the archive of @PROJECT.app holds corpus/keys, a member tarfile's data filter refuses",
                )

    def test_should_leave_nothing_of_the_refused_archive_in_the_cache(self):
        # Arrange
        self.commit_link("corpus/keys", "../../../.ssh/id_ed25519")

        # Act
        with self.assertRaises(BrigadeError):
            prepare_tree(run_process_without_trail, self.create_request(ref="main"))

        # Assert
        self.assertEqual(list((self.cache / "app").iterdir()), [])


class PrepareTreeWhenAnotherExtractionWinsTheRaceTest(PrepareTreeTestCase):
    def setUp(self):
        super().setUp()
        self.sha = self.commit("corpus/tasks.awawa", "committed\n")

    def run_process_extracting_first(self, request):
        record = run_process_without_trail(request)
        if request.argv[:2] == ("git", "archive"):
            winning_tree = self.cache / "app" / self.sha / "corpus"
            winning_tree.mkdir(parents=True)
            (winning_tree / "tasks.awawa").write_text("extracted by the winner\n")
        return record

    def test_should_read_the_tree_the_winner_renamed_into_place_and_leave_it_alone(self):
        # Act
        tree = prepare_tree(self.run_process_extracting_first, self.create_request(ref="main"))

        # Assert
        self.assertEqual(
            ((tree.root / "corpus" / "tasks.awawa").read_text(), list((self.cache / "app").iterdir())),
            ("extracted by the winner\n", [self.cache / "app" / self.sha]),
        )


class PrepareTreeOfAWorktreeTest(PrepareTreeTestCase):
    def setUp(self):
        super().setUp()
        self.commit("corpus/tasks.awawa", "committed on main\n")
        self.feature_tree = self.workspace / "feature-tree"
        run_git(self.repository, "worktree", "add", "--quiet", "-b", "feature", str(self.feature_tree))
        self.feature_sha = self.commit_in(self.feature_tree, "committed on feature\n")
        (self.feature_tree / "corpus" / "tasks.awawa").write_text("edited on feature, not committed\n")

    def commit_in(self, worktree: Path, content: str) -> str:
        (worktree / "corpus" / "tasks.awawa").write_text(content)
        run_git(worktree, *IDENTITY, "commit", "--quiet", "--all", "-m", "edit the tasks")
        return run_git(worktree, "rev-parse", "HEAD").strip()

    def test_should_read_the_worktree_of_the_branch_in_place_uncommitted_edits_visible(self):
        # Act
        tree = prepare_tree(run_process_without_trail, self.create_request(ref="worktree:feature"))

        # Assert
        self.assertEqual(
            (tree, (tree.root / "corpus" / "tasks.awawa").read_text()),
            (
                Tree(
                    project="app", ref="worktree:feature", sha=self.feature_sha, kind="worktree", root=self.feature_tree
                ),
                "edited on feature, not committed\n",
            ),
        )

    def test_should_read_a_worktree_on_a_detached_head_by_its_path(self):
        # Arrange
        detached_tree = self.workspace / "detached-tree"
        run_git(self.repository, "worktree", "add", "--quiet", "--detach", str(detached_tree), "feature")

        # Act
        tree = prepare_tree(run_process_without_trail, self.create_request(worktree=detached_tree))

        # Assert
        self.assertEqual(tree, Tree(project="app", ref=None, sha=self.feature_sha, kind="worktree", root=detached_tree))

    def test_should_refuse_a_branch_no_worktree_holds_naming_it(self):
        # Arrange
        run_git(self.repository, "branch", "ghost")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            prepare_tree(run_process_without_trail, self.create_request(ref="worktree:ghost"))

        # Assert
        self.assertEqual(str(raised.exception), "no worktree of @PROJECT.app has the branch ghost checked out")

    def test_should_refuse_a_path_no_worktree_of_the_project_holds_naming_it(self):
        # Arrange
        elsewhere = self.workspace / "elsewhere"

        # Act
        with self.assertRaises(BrigadeError) as raised:
            prepare_tree(run_process_without_trail, self.create_request(worktree=elsewhere))

        # Assert
        self.assertEqual(str(raised.exception), f"no worktree of @PROJECT.app is at {elsewhere}")


class PrepareTreeOverTheCacheBoundTest(PrepareTreeTestCase):
    def setUp(self):
        super().setUp()
        self.sha_a = self.commit("tasks.awawa", "a" * 1000)
        self.sha_b = self.commit("tasks.awawa", "b" * 1000)
        self.sha_c = self.commit("tasks.awawa", "c" * 1000)

    def test_should_remove_the_least_recently_read_trees_until_the_cache_is_under_the_bound(self):
        # Arrange
        prepare_tree(
            run_process_without_trail, self.create_request(ref=self.sha_a, cache_bound_bytes=2500, now=FIRST_READ)
        )
        prepare_tree(
            run_process_without_trail, self.create_request(ref=self.sha_b, cache_bound_bytes=2500, now=SECOND_READ)
        )
        prepare_tree(
            run_process_without_trail, self.create_request(ref=self.sha_a, cache_bound_bytes=2500, now=THIRD_READ)
        )

        # Act
        prepare_tree(
            run_process_without_trail, self.create_request(ref=self.sha_c, cache_bound_bytes=2500, now=FOURTH_READ)
        )

        # Assert
        self.assertEqual(
            set((self.cache / "app").iterdir()), {self.cache / "app" / self.sha_a, self.cache / "app" / self.sha_c}
        )

    def test_should_keep_the_tree_being_read_whatever_the_bound(self):
        # Arrange
        no_room = 0
        prepare_tree(
            run_process_without_trail, self.create_request(ref=self.sha_a, cache_bound_bytes=no_room, now=FIRST_READ)
        )

        # Act
        prepare_tree(
            run_process_without_trail, self.create_request(ref=self.sha_b, cache_bound_bytes=no_room, now=SECOND_READ)
        )

        # Assert
        self.assertEqual(list((self.cache / "app").iterdir()), [self.cache / "app" / self.sha_b])


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class PrepareTreeWhereTheMachineRefusesAWriteTest(PrepareTreeTestCase):
    def setUp(self):
        super().setUp()
        self.sha = self.commit("corpus/tasks.awawa", "committed\n")

    def tearDown(self):
        self.refused.chmod(0o700)
        super().tearDown()

    def refuse_writes_in(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        directory.chmod(0o500)
        self.refused = directory

    def run_process_refusing_the_extraction(self, request):
        record = run_process_without_trail(request)
        if request.argv[:2] == ("git", "archive"):
            self.refuse_writes_in(Path(request.argv[3].removeprefix("--output=")).parent)
        return record

    def test_should_name_the_cache_it_cannot_create(self):
        # Arrange
        self.refuse_writes_in(self.cache.parent)

        # Act
        with self.assertRaises(CannotWrite) as raised:
            prepare_tree(run_process_without_trail, self.create_request(ref="main"))

        # Assert
        self.assertEqual(str(raised.exception), f"cannot write {self.cache}: Permission denied")

    def test_should_name_the_tree_it_cannot_stage(self):
        # Arrange
        self.refuse_writes_in(self.cache / "app")

        # Act
        with self.assertRaises(CannotWrite) as raised:
            prepare_tree(run_process_without_trail, self.create_request(ref="main"))

        # Assert
        self.assertEqual(str(raised.exception), f"cannot write {self.cache / 'app' / self.sha}: Permission denied")

    def test_should_name_the_tree_it_cannot_extract(self):
        # Act
        with self.assertRaises(CannotWrite) as raised:
            prepare_tree(self.run_process_refusing_the_extraction, self.create_request(ref="main"))

        # Assert
        self.assertEqual(str(raised.exception), f"cannot write {self.cache / 'app' / self.sha}: Permission denied")


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class PrepareTreeWhereTheMachineRefusesThePruningTest(PrepareTreeTestCase):
    def setUp(self):
        super().setUp()
        self.commit("corpus/tasks.awawa", "committed\n")
        self.stale_project = self.cache / "other"
        self.stale_tree = self.stale_project / ("0" * 40)
        (self.stale_tree / "corpus").mkdir(parents=True)
        (self.stale_tree / "corpus" / "tasks.awawa").write_text("stale\n")

    def tearDown(self):
        self.refused.chmod(0o700)
        super().tearDown()

    def restrict(self, directory: Path, mode: int) -> None:
        directory.chmod(mode)
        self.refused = directory

    def test_should_name_the_tree_it_cannot_remove(self):
        # Arrange
        self.restrict(self.stale_project, 0o500)

        # Act
        with self.assertRaises(CannotWrite) as raised:
            prepare_tree(run_process_without_trail, self.create_request(ref="main", cache_bound_bytes=0))

        # Assert
        self.assertEqual(str(raised.exception), f"cannot write {self.stale_tree}: Permission denied")

    def test_should_name_the_project_cache_it_cannot_list(self):
        # Arrange
        self.restrict(self.stale_project, 0o300)

        # Act
        with self.assertRaises(CannotWrite) as raised:
            prepare_tree(run_process_without_trail, self.create_request(ref="main", cache_bound_bytes=0))

        # Assert
        self.assertEqual(str(raised.exception), f"cannot write {self.stale_project}: Permission denied")

    def test_should_name_the_file_it_cannot_measure(self):
        # Arrange
        self.restrict(self.stale_tree / "corpus", 0o600)

        # Act
        with self.assertRaises(CannotWrite) as raised:
            prepare_tree(run_process_without_trail, self.create_request(ref="main", cache_bound_bytes=0))

        # Assert
        self.assertEqual(
            str(raised.exception), f"cannot write {self.stale_tree / 'corpus' / 'tasks.awawa'}: Permission denied"
        )


class PrepareTreeOverAnEntryOfTheCacheItCannotUseTest(PrepareTreeTestCase):
    def setUp(self):
        super().setUp()
        self.sha = self.commit("corpus/tasks.awawa", "committed\n")
        self.tree_root = self.cache / "app" / self.sha
        self.tree_root.parent.mkdir(parents=True)

    def test_should_name_the_tree_it_cannot_place(self):
        # Arrange
        self.tree_root.write_text("")

        # Act
        with self.assertRaises(CannotWrite) as raised:
            prepare_tree(run_process_without_trail, self.create_request(ref="main"))

        # Assert
        self.assertEqual(str(raised.exception), f"cannot write {self.tree_root}: Not a directory")

    @unittest.skipIf(os.geteuid() == 0, "root dates what another user owns")
    def test_should_name_the_cached_tree_it_cannot_date(self):
        # Arrange
        self.tree_root.symlink_to(A_DIRECTORY_OF_ANOTHER_OWNER)

        # Act
        with self.assertRaises(CannotWrite) as raised:
            prepare_tree(run_process_without_trail, self.create_request(ref="main"))

        # Assert
        self.assertEqual(str(raised.exception), f"cannot write {self.tree_root}: Operation not permitted")
