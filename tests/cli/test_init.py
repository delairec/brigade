import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import TemporaryMachine


class BrigadeInitOnAFreshMachineTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name))

    def tearDown(self):
        self.root.cleanup()

    def test_should_print_the_report_as_text(self):
        # Act
        completed = self.machine.run_init()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        corpus = self.machine.corpus
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                f"created  repository   {corpus}",
                f"created  schema       {corpus / '_schema.awawa'}",
                f"created  .gitignore   {corpus / '.gitignore'}",
                f"created  config.toml  {corpus / 'config.toml'}",
                "",
                "init: created 4 · present 0 · differs 0",
            ],
        )
        self.assertEqual(completed.stderr, "")

    def test_should_write_its_command_trail_alone_in_the_state_root_and_create_no_cache_root(self):
        # Act
        self.machine.run_init()

        # Assert
        self.assertEqual(
            [list((self.machine.state_home / "brigade").iterdir()), (self.machine.cache_home / "brigade").exists()],
            [[self.machine.state_home / "brigade" / "commands"], False],
        )
