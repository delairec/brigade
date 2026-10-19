import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.prepare_tree import Tree
from brigade.system.read_configuration import Configuration
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers


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
        request = SimpleNamespace(project="shop", ref=None, worktree=Path("/srv/worktrees/b42"))

        # Act
        tree = prepare_project_tree(request, Configuration(), create_test_runtime(paths, run_process=runner))

        # Assert
        self.assertEqual(
            tree, Tree(project="shop", ref=None, sha="2222222", kind="worktree", root=Path("/srv/worktrees/b42"))
        )
