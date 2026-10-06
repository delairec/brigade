import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, REPOSITORY_ROOT, TemporaryMachine

README = REPOSITORY_ROOT / "README.md"
BEGIN_MARKER = "<!-- adapter matrix: begin -->\n"
END_MARKER = "<!-- adapter matrix: end -->"


def _read_marked_block(readme: str) -> str:
    return readme.partition(BEGIN_MARKER)[2].partition(END_MARKER)[0]


class ReadmeAdapterMatrixTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name)
        self.machine = TemporaryMachine(root)
        self.directory_without_adapter = root / "bin"
        self.directory_without_adapter.mkdir()

    def tearDown(self):
        self.root.cleanup()

    def test_should_hold_the_markdown_matrix_of_the_built_in_adapters(self):
        # Arrange
        environment = {**self.machine.describe_environment(), "PATH": str(self.directory_without_adapter)}
        readme = README.read_text(encoding="utf-8")

        # Act
        completed = self.machine.run_brigade(
            CLONE_ENTRY_POINT, "adapter", "matrix", "--markdown", environment=environment
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            _read_marked_block(readme),
            completed.stdout,
            f"README.md must hold, between {BEGIN_MARKER.strip()} and {END_MARKER}, the block brigade adapter matrix"
            f" --markdown prints:\n{completed.stdout}",
        )
