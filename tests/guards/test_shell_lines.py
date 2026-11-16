import tempfile
import unittest
from pathlib import Path

from tests.guards.find_shell_lines import find_shell_lines

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "brigade"


class ShellLinesOfTheBrigadePackageTest(unittest.TestCase):
    def test_should_find_no_command_handed_to_a_shell_in_the_modules_and_the_templates(self):
        # Act
        violations = find_shell_lines(PACKAGE_ROOT)

        # Assert
        self.assertEqual(violations, [])


class ShellLinesGuardTest(unittest.TestCase):
    def inspect(self, file_path: str, content: str) -> list[str]:
        with tempfile.TemporaryDirectory() as root:
            guarded_file = Path(root) / file_path
            guarded_file.parent.mkdir(parents=True)
            guarded_file.write_text(content)
            return find_shell_lines(Path(root) / "brigade")

    def test_should_flag_a_module_handing_a_command_to_a_shell(self):
        # Arrange
        rows = [
            (
                'argv = ["sh", "-c", script]\n',
                "brigade/adapters/client.py:1 builds an argv opening on the shell sh",
            ),
            (
                'argv = ("/bin/bash", "-c", script)\n',
                "brigade/adapters/client.py:1 builds an argv opening on the shell /bin/bash",
            ),
            (
                "import subprocess\nsubprocess.run(line, shell=True)\n",
                "brigade/adapters/client.py:2 passes shell=True",
            ),
            (
                "import os\nos.system(line)\n",
                "brigade/adapters/client.py:2 calls os.system",
            ),
            (
                "import os\nos.popen(line)\n",
                "brigade/adapters/client.py:2 calls os.popen",
            ),
        ]
        for source, expected_violation in rows:
            with self.subTest(source=source):
                # Act
                violations = self.inspect("brigade/adapters/client.py", source)

                # Assert
                self.assertEqual(violations, [expected_violation])

    def test_should_flag_a_shell_operator_in_a_value_of_an_argv(self):
        # Arrange
        rows = [
            ('argv = ("mkdir", "-p", "state", "&&", "true")\n', "&&"),
            ('argv = ["git", "log", "2>>log"]\n', ">"),
            ('argv = ["date", "$(id -u)"]\n', "$("),
            ('argv = ["date", "`id -u`"]\n', "`"),
            ('argv = ["[", "-e", "hold", "]"]\n', "["),
            ('argv = ["test", "-e", "hold"]\n', "test"),
        ]
        for source, operator in rows:
            with self.subTest(source=source):
                # Act
                violations = self.inspect("brigade/tick/run_checks.py", source)

                # Assert
                self.assertEqual(
                    violations, [f"brigade/tick/run_checks.py:1 puts the shell operator {operator} in an argv"]
                )

    def test_should_leave_an_argv_of_plain_words_and_a_shell_named_as_a_label(self):
        # Arrange
        rows = [
            'argv = ("git", "log", "--format=%H %s", "--", "corpus")\n',
            'argv = [sys.executable, entry_point, "run", "stop-hook", "--at", epoch]\n',
            'message = "the role has a shell: " + name\n',
            'capabilities = ("read", "shell")\n',
            "import subprocess\nsubprocess.run(argv, shell=False)\n",
            'tools = {"shell": ("bash",)}\n',
            'tools = ("bash", "read_file")\n',
            'scripts = ("test", "lint", "typecheck")\n',
            'asset = ("dashboard.css", "text/css; charset=utf-8")\n',
        ]
        for source in rows:
            with self.subTest(source=source):
                # Act
                violations = self.inspect("brigade/tick/run_checks.py", source)

                # Assert
                self.assertEqual(violations, [])

    def test_should_flag_a_shell_operator_in_a_command_line_of_a_shipped_template(self):
        # Arrange
        rows = [
            (
                "brigade/adapters/schedulers/data/crontab-line.tpl",
                "*/5 * * * * mkdir -p ${state} && ${brigade} tick --once >/dev/null 2>>${log}\n",
                "brigade/adapters/schedulers/data/crontab-line.tpl:1 puts the shell operator && in a command line",
            ),
            (
                "brigade/adapters/schedulers/data/brigade.service.tpl",
                "[Service]\nExecStart=/bin/sh -c '${brigade} tick --once'\n",
                "brigade/adapters/schedulers/data/brigade.service.tpl:2 runs a shell in a command line",
            ),
            (
                "brigade/adapters/schedulers/data/brigade.service.tpl",
                "[Service]\nExecStart=${brigade} tick --once 2>>${log}\n",
                "brigade/adapters/schedulers/data/brigade.service.tpl:2 puts the shell operator > in a command line",
            ),
        ]
        for template_path, content, expected_violation in rows:
            with self.subTest(content=content):
                # Act
                violations = self.inspect(template_path, content)

                # Assert
                self.assertEqual(violations, [expected_violation])

    def test_should_leave_the_prose_of_a_template_that_holds_no_command_line(self):
        # Arrange
        rows = [
            ("brigade/tick/data/build-brief.md.tpl", "Push with `git push` && open the pull request > now.\n"),
            ("brigade/adapters/schedulers/data/brigade.service.tpl", "[Unit]\nDescription=brigade tick > log\n"),
            (
                "brigade/adapters/schedulers/data/crontab-line.tpl",
                "*/5 * * * * env ${environment} ${brigade} tick --once\n",
            ),
        ]
        for template_path, content in rows:
            with self.subTest(template=template_path):
                # Act
                violations = self.inspect(template_path, content)

                # Assert
                self.assertEqual(violations, [])
