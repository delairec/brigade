import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

CLONE_ENTRY_POINT = Path(__file__).resolve().parents[2] / "bin" / "brigade"
EXECUTABLES = Path(__file__).resolve().parent / "fixtures" / "executables"

GIT = str(EXECUTABLES / "git-2.47.3")
GIT_FAILING = str(EXECUTABLES / "git-failing")
AWAWA = str(EXECUTABLES / "awawa-2.7.0")
AWAWA_BELOW_FLOOR = str(EXECUTABLES / "awawa-2.6.3")
SYSTEMD_RUNNING = str(EXECUTABLES / "systemd-running")
SYSTEMD_OFFLINE = str(EXECUTABLES / "systemd-offline")
SYSTEMD_NO_BUS = str(EXECUTABLES / "systemd-no-bus")
GH_ACTIVE = str(EXECUTABLES / "gh-active")
GH_LOGGED_OUT = str(EXECUTABLES / "gh-logged-out")
AWAWA_WEB = str(EXECUTABLES / "awawa-web")

PYTHON_ENTRY = 0
GIT_ENTRY = 1
AWAWA_ENTRY = 2
SCHEDULER_ENTRY = 3
FORGE_ENTRY = 4
AWAWA_WEB_ENTRY = 5


def run_doctor(path_directories, *options):
    environment = {"PATH": os.pathsep.join(path_directories)}
    return subprocess.run(
        [sys.executable, CLONE_ENTRY_POINT, "doctor", *options],
        capture_output=True,
        text=True,
        env=environment,
    )


class BrigadeDoctorOnAMachineWithEveryItem(unittest.TestCase):
    def test_should_report_every_item_ok_in_the_versioned_document(self):
        # Arrange
        every_item = [GIT, AWAWA, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB]

        # Act
        completed = run_doctor(every_item, "--json")

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
                    {"name": "git", "kind": "prerequisite", "state": "ok", "detail": "2.47.3 (no floor)", "fallback": None},
                    {"name": "awawa", "kind": "prerequisite", "state": "ok", "detail": "2.7.0 (floor 2.7)", "fallback": None},
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
                ],
            },
        )

    def test_should_print_the_report_as_text(self):
        # Arrange
        every_item = [GIT, AWAWA, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB]

        # Act
        completed = run_doctor(every_item)

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
                "optional",
                "ok       scheduler    user systemd instance running       else: a cron line, or brigade tick --loop",
                "ok       forge        gh as octo-bot                      else: local mode without a forge",
                "ok       awawa-web    on PATH                             else: the dashboard's corpus view only",
                "",
                "doctor: 3 of 3 prerequisites ok · 0 optional items on their fallback",
            ],
        )


class BrigadeDoctorWhenAPrerequisiteFails(unittest.TestCase):
    def test_should_report_the_finding_and_exit_1(self):
        rows = [
            (
                "git missing",
                [AWAWA, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB],
                GIT_ENTRY,
                {"name": "git", "kind": "prerequisite", "state": "finding", "detail": "not on PATH", "fallback": None},
            ),
            (
                "awawa missing",
                [GIT, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB],
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
                [GIT, AWAWA_BELOW_FLOOR, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB],
                AWAWA_ENTRY,
                {
                    "name": "awawa",
                    "kind": "prerequisite",
                    "state": "finding",
                    "detail": "2.6.3 (floor 2.7)",
                    "fallback": None,
                },
            ),
        ]
        for machine, path_directories, entry, expected_entry in rows:
            with self.subTest(machine=machine):
                # Act
                completed = run_doctor(path_directories, "--json")

                # Assert
                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertEqual(json.loads(completed.stdout)["items"][entry], expected_entry)


class BrigadeDoctorWhenAToolFails(unittest.TestCase):
    def test_should_name_the_failed_command_on_stderr_and_exit_1(self):
        # Arrange
        git_failing = [GIT_FAILING, AWAWA, SYSTEMD_RUNNING, GH_ACTIVE, AWAWA_WEB]

        # Act
        completed = run_doctor(git_failing, "--json")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(
            completed.stderr,
            "brigade doctor: git --version exited 128: fatal: unable to access '/etc/gitconfig': Permission denied\n",
        )


class BrigadeDoctorWhenAnOptionalItemIsMissing(unittest.TestCase):
    def test_should_report_a_warning_with_its_fallback_and_exit_0(self):
        rows = [
            (
                "systemctl missing",
                [GIT, AWAWA, GH_ACTIVE, AWAWA_WEB],
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
                [GIT, AWAWA, SYSTEMD_OFFLINE, GH_ACTIVE, AWAWA_WEB],
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
                [GIT, AWAWA, SYSTEMD_NO_BUS, GH_ACTIVE, AWAWA_WEB],
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
                [GIT, AWAWA, SYSTEMD_RUNNING, AWAWA_WEB],
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
                [GIT, AWAWA, SYSTEMD_RUNNING, GH_LOGGED_OUT, AWAWA_WEB],
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
                [GIT, AWAWA, SYSTEMD_RUNNING, GH_ACTIVE],
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
        for machine, path_directories, entry, expected_entry in rows:
            with self.subTest(machine=machine):
                # Act
                completed = run_doctor(path_directories, "--json")

                # Assert
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(json.loads(completed.stdout)["items"][entry], expected_entry)


class BrigadeDoctorAsTextWithAFindingAndAWarning(unittest.TestCase):
    def test_should_name_the_fallback_and_count_what_failed(self):
        # Arrange
        awawa_below_floor_and_no_awawa_web = [GIT, AWAWA_BELOW_FLOOR, SYSTEMD_RUNNING, GH_ACTIVE]

        # Act
        completed = run_doctor(awawa_below_floor_and_no_awawa_web)

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines()[2:],
            [
                "ok       git          2.47.3 (no floor)",
                "finding  awawa        2.6.3 (floor 2.7)",
                "optional",
                "ok       scheduler    user systemd instance running       else: a cron line, or brigade tick --loop",
                "ok       forge        gh as octo-bot                      else: local mode without a forge",
                "warning  awawa-web    not on PATH                         fallback: the dashboard's corpus view only",
                "",
                "doctor: 2 of 3 prerequisites ok · 1 optional item on its fallback",
            ],
        )
