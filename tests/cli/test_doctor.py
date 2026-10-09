import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.cli.forward_coverage_environment import forward_coverage_environment

CLONE_ENTRY_POINT = Path(__file__).resolve().parents[2] / "bin" / "brigade"
EXECUTABLES = Path(__file__).resolve().parent / "fixtures" / "executables"

GIT = str(EXECUTABLES / "git-2.47.3")
GIT_FAILING = str(EXECUTABLES / "git-failing")
AWAWA = str(EXECUTABLES / "awawa-2.7.0")
AWAWA_BELOW_FLOOR = str(EXECUTABLES / "awawa-2.6.3")
AWAWA_NIGHTLY = str(EXECUTABLES / "awawa-nightly")
SYSTEMD_RUNNING = str(EXECUTABLES / "systemd-running")
SYSTEMD_OFFLINE = str(EXECUTABLES / "systemd-offline")
SYSTEMD_NO_BUS = str(EXECUTABLES / "systemd-no-bus")
GH_ACTIVE = str(EXECUTABLES / "gh-active")
GH_LOGGED_OUT = str(EXECUTABLES / "gh-logged-out")
AWAWA_WEB = str(EXECUTABLES / "awawa-web")
CLAUDE = str(EXECUTABLES / "claude-2.1.291")

CLAUDE_CODE_CONFIGURATION = 'client = "claude-code"\n'

PYTHON_ENTRY = 0
GIT_ENTRY = 1
AWAWA_ENTRY = 2
CLIENT_ENTRY = 3
SCHEDULER_ENTRY = 4
FORGE_ENTRY = 5
AWAWA_WEB_ENTRY = 6
INSTRUCTIONS_ENTRY = 7
STEPS_ENTRY = 8
CONFIGURATION_ENTRY_AFTER_THE_CLIENT_ITEMS = 8
EVERY_TOOL_BUT_THE_CLIENT = [GIT, AWAWA, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB]
INSTRUCTIONS_FALLBACK = "built-in roles and no instructions package"


class DoctorTestCase(unittest.TestCase):
    def setUp(self):
        self.config_home = tempfile.TemporaryDirectory()
        self.configuration = Path(self.config_home.name) / "brigade" / "config.toml"

    def tearDown(self):
        self.config_home.cleanup()

    def write_configuration(self, content: str) -> None:
        self.configuration.parent.mkdir(parents=True, exist_ok=True)
        self.configuration.write_text(content)

    def run_doctor(self, path_directories, *options):
        environment = {
            "PATH": os.pathsep.join(path_directories),
            "XDG_CONFIG_HOME": self.config_home.name,
            **forward_coverage_environment(),
        }
        return subprocess.run(  # noqa: S603 - the test's own command line
            [sys.executable, CLONE_ENTRY_POINT, "doctor", *options],
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
        self.assertRegex(python_detail, r"^3\.\d+\.\d+ \(floor 3\.11\)$")
        self.assertEqual(
            document,
            {
                "schema_version": 1,
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

    def test_should_print_the_report_as_text(self):
        # Arrange
        self.write_configuration(f'client = "claude-code"\ninstructions = "{self.instructions}"\n')
        every_item = [GIT, AWAWA, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB]

        # Act
        completed = self.run_doctor(every_item)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report_lines = completed.stdout.splitlines()
        self.assertRegex(report_lines[1], r"^ok       python       3\.\d+\.\d+ \(floor 3\.11\)$")
        self.assertEqual(
            report_lines,
            [
                "prerequisites",
                report_lines[1],
                "ok       git          2.47.3 (no floor)",
                "ok       awawa        2.7.0 (floor 2.7)",
                "ok       client       claude-code: 2.1.291 (Claude Code)",
                "optional",
                "ok       scheduler    user systemd instance running       else: a cron line, or brigade tick --loop",
                "ok       forge        gh as octo-bot                      else: local mode without a forge",
                "ok       awawa-web    on PATH                             else: the dashboard's corpus view only",
                f"ok       instructions lint --strict clean in {self.instructions} else: built-in roles and no instructions package",
                "",
                "doctor: 4 of 4 prerequisites ok · 0 optional items on their fallback",
            ],
        )


class BrigadeDoctorWhenAPrerequisiteFailsTest(DoctorTestCase):
    def test_should_report_the_finding_and_exit_1(self):
        rows = [
            (
                "git missing",
                [AWAWA, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB],
                GIT_ENTRY,
                {"name": "git", "kind": "prerequisite", "state": "finding", "detail": "not on PATH", "fallback": None},
            ),
            (
                "awawa missing",
                [GIT, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB],
                AWAWA_ENTRY,
                {
                    "name": "awawa",
                    "kind": "prerequisite",
                    "state": "finding",
                    "detail": "not on PATH (floor 2.7)",
                    "fallback": None,
                },
            ),
            (
                "awawa below its floor",
                [GIT, AWAWA_BELOW_FLOOR, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB],
                AWAWA_ENTRY,
                {
                    "name": "awawa",
                    "kind": "prerequisite",
                    "state": "finding",
                    "detail": "2.6.3 (floor 2.7)",
                    "fallback": None,
                },
            ),
            (
                "awawa with a version that is no release",
                [GIT, AWAWA_NIGHTLY, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB],
                AWAWA_ENTRY,
                {
                    "name": "awawa",
                    "kind": "prerequisite",
                    "state": "finding",
                    "detail": "nightly (floor 2.7)",
                    "fallback": None,
                },
            ),
        ]
        self.write_configuration(CLAUDE_CODE_CONFIGURATION)
        for machine, path_directories, entry, expected_entry in rows:
            with self.subTest(machine=machine):
                # Act
                completed = self.run_doctor(path_directories, "--json")

                # Assert
                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertEqual(json.loads(completed.stdout)["items"][entry], expected_entry)


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


class BrigadeDoctorWhenAnOptionalItemIsMissingTest(DoctorTestCase):
    def test_should_report_a_warning_with_its_fallback_and_exit_0(self):
        rows = [
            (
                "systemctl missing",
                [GIT, AWAWA, CLAUDE, GH_ACTIVE, AWAWA_WEB],
                SCHEDULER_ENTRY,
                {
                    "name": "scheduler",
                    "kind": "optional",
                    "state": "warning",
                    "detail": "systemctl not on PATH",
                    "fallback": "a cron line, or brigade tick --loop",
                },
            ),
            (
                "no user systemd instance",
                [GIT, AWAWA, CLAUDE, SYSTEMD_OFFLINE, GH_ACTIVE, AWAWA_WEB],
                SCHEDULER_ENTRY,
                {
                    "name": "scheduler",
                    "kind": "optional",
                    "state": "warning",
                    "detail": "no user systemd instance (offline)",
                    "fallback": "a cron line, or brigade tick --loop",
                },
            ),
            (
                "systemctl printing no state",
                [GIT, AWAWA, CLAUDE, SYSTEMD_NO_BUS, GH_ACTIVE, AWAWA_WEB],
                SCHEDULER_ENTRY,
                {
                    "name": "scheduler",
                    "kind": "optional",
                    "state": "warning",
                    "detail": "no user systemd instance",
                    "fallback": "a cron line, or brigade tick --loop",
                },
            ),
            (
                "gh missing",
                [GIT, AWAWA, CLAUDE, SYSTEMD_RUNNING, AWAWA_WEB],
                FORGE_ENTRY,
                {
                    "name": "forge",
                    "kind": "optional",
                    "state": "warning",
                    "detail": "gh not on PATH",
                    "fallback": "local mode without a forge",
                },
            ),
            (
                "gh logged in to no account",
                [GIT, AWAWA, CLAUDE, SYSTEMD_RUNNING, GH_LOGGED_OUT, AWAWA_WEB],
                FORGE_ENTRY,
                {
                    "name": "forge",
                    "kind": "optional",
                    "state": "warning",
                    "detail": "gh logged in to no account",
                    "fallback": "local mode without a forge",
                },
            ),
            (
                "awawa-web missing",
                [GIT, AWAWA, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE],
                AWAWA_WEB_ENTRY,
                {
                    "name": "awawa-web",
                    "kind": "optional",
                    "state": "warning",
                    "detail": "not on PATH",
                    "fallback": "the dashboard's corpus view only",
                },
            ),
        ]
        self.write_configuration(CLAUDE_CODE_CONFIGURATION)
        for machine, path_directories, entry, expected_entry in rows:
            with self.subTest(machine=machine):
                # Act
                completed = self.run_doctor(path_directories, "--json")

                # Assert
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(json.loads(completed.stdout)["items"][entry], expected_entry)


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
                "ok       forge        gh as octo-bot                      else: local mode without a forge",
                "warning  awawa-web    not on PATH                         fallback: the dashboard's corpus view only",
                "warning  instructions none configured                     fallback: built-in roles and no instructions package",
                "",
                "doctor: 3 of 4 prerequisites ok · 2 optional items on their fallback",
            ],
        )


class BrigadeDoctorChecksTheClientAdapterTest(DoctorTestCase):
    def test_should_report_a_finding_naming_brigade_init_when_no_configuration_exists(self):
        # Act
        completed = self.run_doctor([GIT, AWAWA, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB], "--json")

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["items"][CLIENT_ENTRY],
            {
                "name": "client",
                "kind": "prerequisite",
                "state": "finding",
                "detail": f"no configuration at {self.configuration}; run brigade init",
                "fallback": None,
            },
        )

    def test_should_report_a_finding_naming_the_client_key_and_the_file_when_no_client_is_configured(self):
        # Arrange
        self.write_configuration('# client = "claude-code"\n')

        # Act
        completed = self.run_doctor([GIT, AWAWA, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB], "--json")

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["items"][CLIENT_ENTRY],
            {
                "name": "client",
                "kind": "prerequisite",
                "state": "finding",
                "detail": f"config.toml names no client: set the client key in {self.configuration}",
                "fallback": None,
            },
        )

    def test_should_report_a_finding_when_the_probe_fails(self):
        rows = [
            ("the client executable missing", 'client = "claude-code"\n', "claude-code: claude not on PATH"),
            (
                "an adapter found nowhere",
                'client = "frobnicate"\n',
                "no client adapter frobnicate: no built-in module and no brigade-client-frobnicate on PATH",
            ),
        ]
        for case, configuration, expected_detail in rows:
            with self.subTest(case=case):
                # Arrange
                self.write_configuration(configuration)

                # Act
                completed = self.run_doctor([GIT, AWAWA, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB], "--json")

                # Assert
                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertEqual(
                    json.loads(completed.stdout)["items"][CLIENT_ENTRY],
                    {
                        "name": "client",
                        "kind": "prerequisite",
                        "state": "finding",
                        "detail": expected_detail,
                        "fallback": None,
                    },
                )

    def test_should_report_a_finding_naming_the_key_of_a_configuration_off_its_shape(self):
        # Arrange
        self.write_configuration("client = 1\n")

        # Act
        completed = self.run_doctor([GIT, AWAWA, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB], "--json")

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["items"][CLIENT_ENTRY],
            {
                "name": "client",
                "kind": "prerequisite",
                "state": "finding",
                "detail": f"client is an integer, not a string, in {self.configuration}",
                "fallback": None,
            },
        )

    def test_should_report_a_finding_naming_a_trail_days_that_is_no_integer_of_1_or_more(self):
        rows = [
            ("zero", "trail_days = 0\n", f"trail_days is 0, not 1 or more, in {self.configuration}"),
            ("a string", 'trail_days = "7"\n', f"trail_days is a string, not an integer, in {self.configuration}"),
        ]
        for case, trail_days, expected_detail in rows:
            with self.subTest(case=case):
                # Arrange
                self.write_configuration(CLAUDE_CODE_CONFIGURATION + trail_days)

                # Act
                completed = self.run_doctor([GIT, AWAWA, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB], "--json")

                # Assert
                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertEqual(
                    json.loads(completed.stdout)["items"][CLIENT_ENTRY],
                    {
                        "name": "client",
                        "kind": "prerequisite",
                        "state": "finding",
                        "detail": expected_detail,
                        "fallback": None,
                    },
                )

    def test_should_report_a_finding_naming_a_journal_poll_that_is_no_positive_number(self):
        rows = [
            ("zero", "journal_poll_s = 0\n", f"journal_poll_s is 0, not a positive number, in {self.configuration}"),
            (
                "a string",
                'journal_poll_s = "2"\n',
                f"journal_poll_s is a string, not a positive number, in {self.configuration}",
            ),
        ]
        for case, journal_poll, expected_problem in rows:
            with self.subTest(case=case):
                # Arrange
                self.write_configuration(CLAUDE_CODE_CONFIGURATION + journal_poll)

                # Act
                completed = self.run_doctor([GIT, AWAWA, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB], "--json")

                # Assert
                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertEqual(
                    json.loads(completed.stdout)["items"][CONFIGURATION_ENTRY_AFTER_THE_CLIENT_ITEMS],
                    {
                        "name": "config",
                        "kind": "prerequisite",
                        "state": "finding",
                        "detail": f"{expected_problem}; the default of 2 s holds",
                        "fallback": None,
                    },
                )

    def test_should_report_an_adapter_with_no_client_executable_as_ok(self):
        # Arrange
        self.write_configuration('client = "fake"\n')

        # Act
        completed = self.run_doctor([GIT, AWAWA, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB], "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["items"][CLIENT_ENTRY],
            {
                "name": "client",
                "kind": "prerequisite",
                "state": "ok",
                "detail": "fake: no client executable",
                "fallback": None,
            },
        )

    def test_should_warn_that_a_client_counting_no_steps_holds_the_budget_on_the_clock(self):
        # Arrange
        self.write_configuration('client = "fake"\n')

        # Act
        completed = self.run_doctor(EVERY_TOOL_BUT_THE_CLIENT, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["items"][STEPS_ENTRY],
            {
                "name": "steps",
                "kind": "optional",
                "state": "warning",
                "detail": "fake counts no steps: the budget is held on the clock and the run cut at its limit",
                "fallback": "the wall-time limit of each run",
            },
        )


class BrigadeDoctorWithAConfigurationThatIsNotTomlTest(DoctorTestCase):
    def test_should_report_the_error_of_the_one_read_in_each_check_that_needs_the_configuration(self):
        rows = [("client", CLIENT_ENTRY, "finding"), ("instructions", INSTRUCTIONS_ENTRY, "warning")]
        self.write_configuration('client = "claude-code\n')
        for check, entry, expected_state in rows:
            with self.subTest(check=check):
                # Act
                completed = self.run_doctor([GIT, AWAWA, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB], "--json")

                # Assert
                item = json.loads(completed.stdout)["items"][entry]
                self.assertEqual(item["state"], expected_state)
                self.assertIn(f"{self.configuration} is not valid TOML: ", item["detail"])

    def test_should_report_no_steps_item_since_no_client_could_be_probed(self):
        # Arrange
        self.write_configuration('client = "claude-code\n')

        # Act
        completed = self.run_doctor([GIT, AWAWA, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB], "--json")

        # Assert
        self.assertEqual(len(json.loads(completed.stdout)["items"]), STEPS_ENTRY)

    def test_should_report_no_instructions_configured_when_no_configuration_exists(self):
        # Act
        completed = self.run_doctor([GIT, AWAWA, CLAUDE, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB], "--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout)["items"][INSTRUCTIONS_ENTRY],
            {
                "name": "instructions",
                "kind": "optional",
                "state": "warning",
                "detail": "none configured",
                "fallback": INSTRUCTIONS_FALLBACK,
            },
        )


INSTRUCTIONS_SCHEMA = (
    'SCHEMA AGENT\n\tDESC "a role"\n\tFIELD WORK string\n\t\tREQUIRED\n\t\tREPEATABLE\n'
    "\tFIELD REASONING deepest|deep|standard|light\n\t\tREQUIRED\n"
)
CLEAN_AGENT = 'AGENT planner\n\tWORK "the plan of a wave"\n\tREASONING deep\n'
AGENT_LACKING_ITS_REASONING = 'AGENT planner\n\tWORK "the plan of a wave"\n'


@unittest.skipUnless(shutil.which("awawa"), "awawa is not on PATH")
class BrigadeDoctorReportsTheInstructionsCorpusTest(DoctorTestCase):
    def setUp(self):
        super().setUp()
        self.instructions = Path(self.config_home.name) / "instructions"
        self.instructions.mkdir()
        (self.instructions / "_schema.awawa").write_text(INSTRUCTIONS_SCHEMA)
        self.machine_with_awawa = [GIT, os.path.dirname(shutil.which("awawa")), SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB]

    def test_should_report_a_warning_with_its_fallback_when_none_is_configured(self):
        # Arrange
        self.write_configuration('client = "fake"\n')

        # Act
        completed = self.run_doctor(self.machine_with_awawa, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["items"][INSTRUCTIONS_ENTRY],
            {
                "name": "instructions",
                "kind": "optional",
                "state": "warning",
                "detail": "none configured",
                "fallback": INSTRUCTIONS_FALLBACK,
            },
        )

    def test_should_report_whether_the_configured_corpus_lints_clean(self):
        rows = [
            ("a corpus that lints clean", CLEAN_AGENT, "ok", "lint --strict clean in"),
            ("a corpus with an error", AGENT_LACKING_ITS_REASONING, "warning", "lint --strict fails in"),
        ]
        self.write_configuration(f'client = "fake"\ninstructions = "{self.instructions}"\n')
        for corpus, agents, expected_state, expected_verdict in rows:
            with self.subTest(corpus=corpus):
                # Arrange
                (self.instructions / "agents.awawa").write_text(agents)

                # Act
                completed = self.run_doctor(self.machine_with_awawa, "--json")

                # Assert
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(
                    json.loads(completed.stdout)["items"][INSTRUCTIONS_ENTRY],
                    {
                        "name": "instructions",
                        "kind": "optional",
                        "state": expected_state,
                        "detail": f"{expected_verdict} {self.instructions}",
                        "fallback": INSTRUCTIONS_FALLBACK,
                    },
                )


GH_ACCOUNTS = str(EXECUTABLES / "gh-accounts")
EVERY_TOOL_WITH_THE_ACCOUNTS_GH = [GIT, AWAWA, SYSTEMD_RUNNING, GH_ACCOUNTS, AWAWA_WEB, CLAUDE]
FORGE_ACCOUNTS = '[forge_accounts]\ncli = "octo-bot"\nbuild = "octo-bot"\nverify = "refused-bot"\n'
FORGE_LOGIN_FALLBACK = "the commands acting as it stop"


class BrigadeDoctorReportsTheForgeAccountsTest(DoctorTestCase):
    def test_should_name_the_login_of_cli_on_the_forge_line_and_report_each_login(self):
        # Arrange
        self.write_configuration(CLAUDE_CODE_CONFIGURATION + FORGE_ACCOUNTS)

        # Act
        completed = self.run_doctor(EVERY_TOOL_WITH_THE_ACCOUNTS_GH, "--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout)["items"][FORGE_ENTRY : FORGE_ENTRY + 3],
            [
                {
                    "name": "forge",
                    "kind": "optional",
                    "state": "ok",
                    "detail": "gh as octo-bot",
                    "fallback": "local mode without a forge",
                },
                {
                    "name": "forge login",
                    "kind": "optional",
                    "state": "ok",
                    "detail": "octo-bot for cli, build",
                    "fallback": FORGE_LOGIN_FALLBACK,
                },
                {
                    "name": "forge login",
                    "kind": "optional",
                    "state": "warning",
                    "detail": "gh printed no token for refused-bot, bound to verify",
                    "fallback": FORGE_LOGIN_FALLBACK,
                },
            ],
        )

    def test_should_run_gh_with_no_token_when_cli_is_bound_to_no_login(self):
        # Arrange
        self.write_configuration(CLAUDE_CODE_CONFIGURATION)

        # Act
        completed = self.run_doctor(EVERY_TOOL_WITH_THE_ACCOUNTS_GH, "--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout)["items"][FORGE_ENTRY : FORGE_ENTRY + 2],
            [
                {
                    "name": "forge",
                    "kind": "optional",
                    "state": "ok",
                    "detail": "gh as octo-user",
                    "fallback": "local mode without a forge",
                },
                {
                    "name": "awawa-web",
                    "kind": "optional",
                    "state": "ok",
                    "detail": "on PATH",
                    "fallback": "the dashboard's corpus view only",
                },
            ],
        )

    def test_should_warn_on_the_forge_line_when_gh_prints_no_token_for_the_login_of_cli(self):
        # Arrange
        self.write_configuration(CLAUDE_CODE_CONFIGURATION + '[forge_accounts]\ncli = "refused-bot"\n')

        # Act
        completed = self.run_doctor(EVERY_TOOL_WITH_THE_ACCOUNTS_GH, "--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout)["items"][FORGE_ENTRY],
            {
                "name": "forge",
                "kind": "optional",
                "state": "warning",
                "detail": "gh printed no token for refused-bot",
                "fallback": "local mode without a forge",
            },
        )

    def test_should_warn_on_each_login_when_gh_is_not_on_path(self):
        # Arrange
        self.write_configuration(CLAUDE_CODE_CONFIGURATION + '[forge_accounts]\ncli = "octo-bot"\n')

        # Act
        completed = self.run_doctor([GIT, AWAWA, SYSTEMD_RUNNING, AWAWA_WEB, CLAUDE], "--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout)["items"][FORGE_ENTRY : FORGE_ENTRY + 2],
            [
                {
                    "name": "forge",
                    "kind": "optional",
                    "state": "warning",
                    "detail": "gh not on PATH",
                    "fallback": "local mode without a forge",
                },
                {
                    "name": "forge login",
                    "kind": "optional",
                    "state": "warning",
                    "detail": "gh not on PATH for octo-bot, bound to cli",
                    "fallback": FORGE_LOGIN_FALLBACK,
                },
            ],
        )
