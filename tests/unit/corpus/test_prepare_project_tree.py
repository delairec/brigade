import io
import os
import shutil
import tarfile
import tempfile
import unittest
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.prepare_tree import Tree
from brigade.errors import BrigadeError
from brigade.system.parse_configuration import Configuration
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

LONG_AGO = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
STALE_TREE_BYTES = 2048


class ArchivingProcessRunnerDouble(RecordingProcessRunner):
    def __call__(self, request):
        record = super().__call__(request)
        if request.argv[1] == "archive":
            with tarfile.open(request.argv[3].removeprefix("--output="), "w") as archive:
                member = tarfile.TarInfo("README.md")
                member.size = len(b"# shop\n")
                archive.addfile(member, io.BytesIO(b"# shop\n"))
        return record


class PrepareProjectTreeTest(unittest.TestCase):
    def test_should_prepare_the_tree_of_the_registered_project(self):
        # Arrange
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        paths = create_test_paths(root)
        paths.config_root.mkdir(parents=True)
        paths.schema_file.write_text("SCHEMA PROJECT\n")
        runner = RecordingProcessRunner(
            {
                **create_registry_answers(paths.config_root, {"shop": {"PATH": "/srv/shop"}}),
                ("git", "worktree", "list", "--porcelain", "-z"): ProcessAnswer(
                    stdout="worktree /srv/worktrees/b42\0HEAD 2222222\0branch refs/heads/feat/b42\0\0"
                ),
            }
        )
        request = Namespace(project="shop", ref=None, worktree=Path("/srv/worktrees/b42"))

        # Act
        tree = prepare_project_tree(request, Configuration(), create_test_runtime(paths, run_process=runner))

        # Assert
        self.assertEqual(
            tree, Tree(project="shop", ref=None, sha="2222222", kind="worktree", root=Path("/srv/worktrees/b42"))
        )


class PrepareProjectTreeAtABranchTest(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        self.paths = create_test_paths(root)
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")
        self.cached_tree = self.paths.cache_root / "refs" / "shop" / "2222222"
        self.cached_tree.mkdir(parents=True)
        self.runtime = create_test_runtime(
            self.paths,
            run_process=RecordingProcessRunner(
                {
                    **create_registry_answers(self.paths.config_root, {"shop": {"PATH": "/srv/shop"}}),
                    ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "main^{commit}"): ProcessAnswer(
                        stdout="2222222\n"
                    ),
                }
            ),
        )
        self.request = Namespace(project="shop", ref="main", worktree=None)

    def test_should_read_the_tree_cached_under_the_refs_of_the_cache_root(self):
        # Act
        tree = prepare_project_tree(self.request, Configuration(), self.runtime)

        # Assert
        self.assertEqual(tree, Tree(project="shop", ref="main", sha="2222222", kind="archive", root=self.cached_tree))

    def test_should_take_the_lock_of_the_refs_cache_in_the_lock_directory(self):
        # Act
        prepare_project_tree(self.request, Configuration(), self.runtime)

        # Assert
        self.assertTrue((self.paths.lock_directory / "refs-cache.lock").is_file())


class PrepareProjectTreeUnderTheConfiguredCacheBoundTest(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        self.paths = create_test_paths(root)
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")
        self.stale_tree = self.paths.cache_root / "refs" / "tidepool" / "old999"
        self.stale_tree.mkdir(parents=True)
        (self.stale_tree / "file.bin").write_bytes(b"x" * STALE_TREE_BYTES)
        os.utime(self.stale_tree, (LONG_AGO.timestamp(), LONG_AGO.timestamp()))
        self.runtime = create_test_runtime(
            self.paths,
            run_process=ArchivingProcessRunnerDouble(
                {
                    **create_registry_answers(self.paths.config_root, {"shop": {"PATH": "/srv/shop"}}),
                    ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "main^{commit}"): ProcessAnswer(
                        stdout="2222222\n"
                    ),
                }
            ),
        )
        self.request = Namespace(project="shop", ref="main", worktree=None)

    def test_should_keep_the_trees_refs_cache_mb_holds(self):
        # Arrange
        configuration = Configuration(refs_cache_mb=1)

        # Act
        prepare_project_tree(self.request, configuration, self.runtime)

        # Assert
        self.assertEqual(list(self.stale_tree.parent.iterdir()), [self.stale_tree])

    def test_should_evict_the_trees_beyond_refs_cache_mb(self):
        # Arrange
        configuration = Configuration(refs_cache_mb=0)

        # Act
        prepare_project_tree(self.request, configuration, self.runtime)

        # Assert
        self.assertEqual(list(self.stale_tree.parent.iterdir()), [])


class PrepareProjectTreeWithoutTheOperationalCorpusTest(unittest.TestCase):
    def test_should_refuse_before_looking_the_project_up(self):
        # Arrange
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        request = Namespace(project="ghost", ref="main", worktree=None)
        runtime = create_test_runtime(create_test_paths(root), run_process=RecordingProcessRunner())

        # Act
        with self.assertRaises(BrigadeError) as raised:
            prepare_project_tree(request, Configuration(), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "the operational corpus is missing; run brigade init first")
