import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from tests.process_launcher import ProcessLauncher

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CLONE_ENTRY_POINT = REPOSITORY_ROOT / "bin" / "brigade"
EXECUTABLES = Path(__file__).resolve().parent / "fixtures" / "executables"

GIT = str(EXECUTABLES / "git-2.47.3")
GIT_FAILING = str(EXECUTABLES / "git-failing")
AWAWA = str(EXECUTABLES / "awawa-2.7.0")
AWAWA_BELOW_FLOOR = str(EXECUTABLES / "awawa-2.6.3")
SYSTEMD_RUNNING = str(EXECUTABLES / "systemd-running")
GH_ACTIVE = str(EXECUTABLES / "gh-active")
GH_ACCOUNTS = str(EXECUTABLES / "gh-accounts")
AWAWA_WEB = str(EXECUTABLES / "awawa-web")
CLAUDE = str(EXECUTABLES / "claude-2.1.291")
REAL_GIT = shutil.which("git")

CLAUDE_CODE_CONFIGURATION = 'client = "claude-code"\n'
FORGE_ACCOUNTS = '[forge_accounts]\ncli = "octo-bot"\nbuild = "octo-bot"\nreview = "refused-bot"\n'

PYTHON_ENTRY = 0
EVERY_TOOL_WITH_THE_ACCOUNTS_GH = [GIT, AWAWA, SYSTEMD_RUNNING, GH_ACCOUNTS, AWAWA_WEB, CLAUDE]
EVERY_TOOL_BUT_GIT = [AWAWA, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB]
GIT_ENVIRONMENT = {
    "GIT_AUTHOR_NAME": "brigade tests",
    "GIT_AUTHOR_EMAIL": "tests@brigade.invalid",
    "GIT_AUTHOR_DATE": "2026-10-07T09:00:00Z",
    "GIT_COMMITTER_NAME": "brigade tests",
    "GIT_COMMITTER_EMAIL": "tests@brigade.invalid",
    "GIT_COMMITTER_DATE": "2026-10-07T09:00:00Z",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}
CHECKOUT_FALLBACK = "git pull in the checkout"
LAST_ITEM_BEFORE_THE_CHECKOUT = "instructions"


def run_git(directory: Path, *arguments: str) -> None:
    ProcessLauncher.run(
        [REAL_GIT, *arguments],
        cwd=directory,
        env={**os.environ, **GIT_ENVIRONMENT},
        capture_output=True,
        check=True,
    )


class DoctorTestCase(unittest.TestCase):
    def setUp(self):
        self.config_home = tempfile.TemporaryDirectory()
        self.configuration = Path(self.config_home.name) / "brigade" / "config.toml"
        self.state_home = Path(self.config_home.name) / "state"
        self.gh_record = Path(self.config_home.name) / "gh.txt"

    def tearDown(self):
        self.config_home.cleanup()

    def write_configuration(self, content: str) -> None:
        self.configuration.parent.mkdir(parents=True, exist_ok=True)
        self.configuration.write_text(content)

    def read_every_state_file(self) -> str:
        files = sorted(path for path in self.state_home.rglob("*") if path.is_file())
        return "".join(path.read_text(encoding="utf-8", errors="replace") for path in files)

    def run_doctor(self, path_directories, *options):
        return self.run_doctor_from(CLONE_ENTRY_POINT, path_directories, *options)

    def run_doctor_from(self, entry_point, path_directories, *options):
        environment = {
            "PATH": os.pathsep.join(path_directories),
            "XDG_CONFIG_HOME": self.config_home.name,
            "XDG_STATE_HOME": str(self.state_home),
            "BRIGADE_GH_RECORD": str(self.gh_record),
        }
        return ProcessLauncher.run(
            [sys.executable, entry_point, "doctor", *options],
            capture_output=True,
            text=True,
            env=environment,
            check=False,
        )


class BrigadeDoctorOnAMachineWithEveryItemTest(DoctorTestCase):
    def setUp(self):
        super().setUp()
        self.instructions = self.config_home.name

    def test_should_report_every_item_ok_in_the_versioned_document(self):
        # Arrange
        self.write_configuration(f'client = "claude-code"\ninstructions = "{self.instructions}"\n')
        every_item = [GIT, AWAWA, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB]

        # Act
        completed = self.run_doctor(every_item, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        python_detail = document["items"][PYTHON_ENTRY]["detail"]
        self.assertRegex(python_detail, r"^3\.\d+\.\d+ \(floor 3\.11\.4\)$")
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "client": "claude-code",
                "slot_clients": {},
                "items": [
                    {
                        "name": "python",
                        "kind": "prerequisite",
                        "state": "ok",
                        "detail": python_detail,
                        "fallback": None,
                    },
                    {
                        "name": "git",
                        "kind": "prerequisite",
                        "state": "ok",
                        "detail": "2.47.3 (no floor)",
                        "fallback": None,
                    },
                    {
                        "name": "awawa",
                        "kind": "prerequisite",
                        "state": "ok",
                        "detail": "2.7.0 (floor 2.7)",
                        "fallback": None,
                    },
                    {
                        "name": "client",
                        "kind": "prerequisite",
                        "state": "ok",
                        "detail": "claude-code: 2.1.291 (Claude Code)",
                        "fallback": None,
                    },
                    {
                        "name": "scheduler",
                        "kind": "optional",
                        "state": "ok",
                        "detail": "user systemd instance running",
                        "fallback": "a cron line, or brigade tick --loop",
                    },
                    {
                        "name": "linger",
                        "kind": "optional",
                        "state": "ok",
                        "detail": "the user systemd instance lingers",
                        "fallback": "the tick fires only while a session of the user is open",
                    },
                    {
                        "name": "forge",
                        "kind": "optional",
                        "state": "ok",
                        "detail": "gh as octo-bot",
                        "fallback": "local mode without a forge",
                    },
                    {
                        "name": "awawa-web",
                        "kind": "optional",
                        "state": "ok",
                        "detail": "on PATH",
                        "fallback": "the dashboard's corpus view only",
                    },
                    {
                        "name": "instructions",
                        "kind": "optional",
                        "state": "ok",
                        "detail": f"lint --strict clean in {self.instructions}",
                        "fallback": "built-in roles and no instructions package",
                    },
                ],
            },
        )


class BrigadeDoctorWhenAToolFailsTest(DoctorTestCase):
    def test_should_name_the_failed_command_on_stderr_and_exit_1(self):
        # Arrange
        self.write_configuration(CLAUDE_CODE_CONFIGURATION)
        git_failing = [GIT_FAILING, AWAWA, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB]

        # Act
        completed = self.run_doctor(git_failing, "--json")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(
            completed.stderr,
            "brigade doctor: git --version exited 128: fatal: unable to access '/etc/gitconfig': Permission denied\n",
        )


class BrigadeDoctorAsTextWithAFindingAndAWarningTest(DoctorTestCase):
    def test_should_name_the_fallback_and_count_what_failed(self):
        # Arrange
        self.write_configuration(CLAUDE_CODE_CONFIGURATION)
        awawa_below_floor_and_no_awawa_web = [GIT, AWAWA_BELOW_FLOOR, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE]

        # Act
        completed = self.run_doctor(awawa_below_floor_and_no_awawa_web)

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines()[2:],
            [
                "ok       git          2.47.3 (no floor)",
                "finding  awawa        2.6.3 (floor 2.7)",
                "ok       client       claude-code: 2.1.291 (Claude Code)",
                "optional",
                "ok       scheduler    user systemd instance running       else: a cron line, or brigade tick --loop",
                "ok       linger       the user systemd instance lingers   else: the tick fires only while a session of the user is open",
                "ok       forge        gh as octo-bot                      else: local mode without a forge",
                "warning  awawa-web    not on PATH                         fallback: the dashboard's corpus view only",
                "warning  instructions none configured                     fallback: built-in roles and no instructions package",
                "",
                "doctor: 3 of 4 prerequisites ok · 2 optional items on their fallback",
            ],
        )


class BrigadeDoctorReportsTheForgeAccountsTest(DoctorTestCase):
    def test_should_write_the_token_nowhere(self):
        # Arrange
        self.write_configuration(CLAUDE_CODE_CONFIGURATION + FORGE_ACCOUNTS)

        # Act
        completed = self.run_doctor(EVERY_TOOL_WITH_THE_ACCOUNTS_GH, "--verbose", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("token-of-", completed.stdout + completed.stderr + self.read_every_state_file())


class BrigadeDoctorRunFromACloneTest(DoctorTestCase):
    def setUp(self):
        super().setUp()
        self.machine = tempfile.TemporaryDirectory()
        root = Path(self.machine.name).resolve()
        self.clone = root / "clone"
        self.git_directory = root / "git"
        self.git_directory.mkdir()
        (self.git_directory / "git").symlink_to(REAL_GIT)
        run_git(root, "init", "--quiet", "--bare", "--initial-branch=main", "upstream.git")
        run_git(root, "clone", "--quiet", "upstream.git", "clone")
        run_git(self.clone, "commit", "--quiet", "--allow-empty", "--message=the release the clone runs")
        run_git(self.clone, "push", "--quiet", "origin", "main")
        shutil.copytree(
            REPOSITORY_ROOT / "brigade", self.clone / "brigade", ignore=shutil.ignore_patterns("__pycache__")
        )
        shutil.copytree(REPOSITORY_ROOT / "bin", self.clone / "bin")
        shutil.copy(REPOSITORY_ROOT / "build.py", self.clone)
        self.write_configuration(CLAUDE_CODE_CONFIGURATION)

    def tearDown(self):
        self.machine.cleanup()
        super().tearDown()

    def run_clone_doctor(self, *options):
        return self.run_doctor_from(
            self.clone / "bin" / "brigade", [str(self.git_directory), *EVERY_TOOL_BUT_GIT], *options
        )

    def test_should_report_no_checkout_from_the_zipapp_built_in_the_clone(self):
        # Arrange
        ProcessLauncher.run([sys.executable, self.clone / "build.py"], check=True)
        zipapp = self.clone / "dist" / "brigade.pyz"

        # Act
        completed = self.run_doctor_from(zipapp, [str(self.git_directory), *EVERY_TOOL_BUT_GIT], "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["items"][-1]["name"], LAST_ITEM_BEFORE_THE_CHECKOUT)

    def test_should_warn_that_the_checkout_is_unreadable_when_its_upstream_is_no_longer_fetched(self):
        # Arrange
        run_git(self.clone, "update-ref", "-d", "refs/remotes/origin/main")

        # Act
        completed = self.run_clone_doctor("--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout)["items"][-1],
            {
                "name": "checkout",
                "kind": "optional",
                "state": "warning",
                "detail": f"{self.clone}: git rev-parse --short --verify --end-of-options origin/main exited 128: "
                "fatal: Needed a single revision",
                "fallback": CHECKOUT_FALLBACK,
            },
        )
