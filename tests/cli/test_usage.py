import unittest
from pathlib import Path

from tests.process_launcher import ProcessLauncher

CLONE_ENTRY_POINT = Path(__file__).resolve().parents[2] / "bin" / "brigade"


class BrigadeUsageWhenNoOptionIsGivenTest(unittest.TestCase):
    def test_should_refuse_with_its_usage(self):
        # Act
        completed = ProcessLauncher.run([CLONE_ENTRY_POINT], capture_output=True, text=True, check=False)

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn("usage: brigade", completed.stderr)


class BrigadeUsageWhenAnUnknownOptionIsGivenTest(unittest.TestCase):
    def test_should_refuse_naming_the_option(self):
        # Act
        completed = ProcessLauncher.run(
            [CLONE_ENTRY_POINT, "--frobnicate"], capture_output=True, text=True, check=False
        )

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn("unrecognized arguments: --frobnicate", completed.stderr)


class BrigadeUsageWhenOnlyTheJsonOptionIsGivenTest(unittest.TestCase):
    def test_should_refuse_as_when_no_option_is_given(self):
        # Act
        completed = ProcessLauncher.run([CLONE_ENTRY_POINT, "--json"], capture_output=True, text=True, check=False)

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn("brigade: error: no option given", completed.stderr)


class BrigadeUsageWhenAGroupIsGivenNoActionTest(unittest.TestCase):
    def test_should_refuse_with_the_usage_of_the_group(self):
        # Act
        completed = ProcessLauncher.run([CLONE_ENTRY_POINT, "runs"], capture_output=True, text=True, check=False)

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(
            completed.stderr,
            "usage: brigade runs [-h] [--json] [--verbose] action ...\n"
            "brigade runs: error: the following arguments are required: action\n",
        )


class BrigadeUsageWhenAnUnknownActionIsGivenTest(unittest.TestCase):
    def test_should_refuse_naming_every_action_of_the_group(self):
        # Act
        completed = ProcessLauncher.run(
            [CLONE_ENTRY_POINT, "runs", "frobnicate"], capture_output=True, text=True, check=False
        )

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertRegex(
            completed.stderr, r"invalid choice: 'frobnicate' \(choose from '?list'?, '?prune'?, '?show'?, '?stop'?\)\n"
        )


class BrigadeUsageWhenAnUnknownCommandIsGivenTest(unittest.TestCase):
    def test_should_refuse_naming_every_command(self):
        # Act
        completed = ProcessLauncher.run([CLONE_ENTRY_POINT, "frobnicate"], capture_output=True, text=True, check=False)

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertRegex(completed.stderr, r"invalid choice: 'frobnicate' \(choose from '?adapter'?, .+, '?wave'?\)\n")


class BrigadeUsageWhenACommandLineMissesAnArgumentTest(unittest.TestCase):
    def test_should_refuse_with_the_usage_of_the_command_line(self):
        # Act
        completed = ProcessLauncher.run(
            [CLONE_ENTRY_POINT, "runs", "show"], capture_output=True, text=True, check=False
        )

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertIn("brigade runs show: error: the following arguments are required:", completed.stderr)
