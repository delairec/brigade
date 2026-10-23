import json
import os
import sys
import tempfile
import time
from pathlib import Path

from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, FileWaitingTestCase
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, REPOSITORY_ROOT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject
from tests.cli.test_collect import install_executable

FORGE = REPOSITORY_ROOT / "tests" / "cli" / "fixtures" / "executables" / "github-over-a-bare-remote"
REMOTE_URL = "https://github.com/sandbox/shop.git"
REHEARSAL_WAIT_S = 120
TICK_INTERVAL_S = 0.2
SANDBOX_SCHEMA = (
    "SCHEMA TASK\n"
    '\tDESC "a change delivered by one pull request"\n'
    "\tFIELD TITLE string\n\t\tREQUIRED\n"
    "\tFIELD STATUS todo|implemented\n\t\tREQUIRED\n"
    "\tFIELD TYPE feat|fix|test|docs\n\t\tREQUIRED\n"
    "\tFIELD MILESTONE @MILESTONE\n"
    "\tFIELD AFTER @TASK\n\t\tREPEATABLE\n"
    "\tFIELD DELIVERED_BY uint\n"
    "\n"
    "SCHEMA MILESTONE\n"
    '\tDESC "the tasks planned for one request"\n'
    "\tFIELD TITLE string\n\t\tREQUIRED\n"
    "\tFIELD STATUS planned|running|reached\n\t\tREQUIRED\n"
)
SANDBOX_TASKS = 'TASK S0\n\tTITLE "Show the cart"\n\tSTATUS implemented\n\tTYPE feat\n'
PLAN = (
    'MILESTONE M1\n\tTITLE "Empty cart"\n\tSTATUS planned\n\n'
    'TASK S1\n\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tTYPE feat\n\tMILESTONE @MILESTONE.M1\n\n'
    'TASK S2\n\tTITLE "Confirm before emptying the cart"\n\tSTATUS todo\n\tTYPE feat\n\tMILESTONE @MILESTONE.M1\n'
    "\tAFTER @TASK.S1\n\n"
    'TASK S3\n\tTITLE "Count the emptied carts"\n\tSTATUS todo\n\tTYPE feat\n\tMILESTONE @MILESTONE.M1\n'
)
READ_THE_BRIEF = '#!/bin/sh\nbrief=$(cat)\nread_argument() { printf \'%s\\n\' "$brief" | sed -n "s/^$1=//p"; }\n'
PLANNER_PLAY = (
    READ_THE_BRIEF + 'plan="$BRIGADE_RUN_DIR/plan.awawa"\n'
    f"cat > \"$plan\" <<'PLAN'\n{PLAN}PLAN\n"
    'brigade plan record "$(read_argument request)" --file "$plan" >&2\n'
    'cat -- "$1"\n'
)
BUILDER_PLAY = (
    READ_THE_BRIEF + 'task=$(read_argument task | sed "s/^@TASK\\.//")\n'
    'printf \'%s\\n\' "$task" > "delivered-$task.txt"\n'
    'git add -- "delivered-$task.txt" && git commit --quiet -m "feat: deliver $task" >&2\n'
    'brigade task check >&2 && brigade task pr --subject "deliver $task" >&2 && brigade task promote >&2\n'
    'cat -- "$1"\n'
)
REVIEWER_PLAY = (
    READ_THE_BRIEF + 'verdict="$BRIGADE_RUN_DIR/verdict.json"\n'
    'printf \'{"head": "%s", "verdict": "pass", "findings": []}\\n\' "$(git rev-parse HEAD)" > "$verdict"\n'
    'brigade verify verdict "$(read_argument pr)" --file "$verdict" >&2\n'
    'cat -- "$1"\n'
)
FORGE_ACCOUNTS = (
    '[forge_accounts]\ncli = "octo-cli"\nplan = "octo-plan"\nbuild = "octo-build"\nreview = "octo-review"\n'
)


def list_merged_tasks(events: list[dict]) -> list[str]:
    return sorted(event["task"] for event in events if event["state"] == "merged")


def list_runs(events: list[dict]) -> list[str]:
    return sorted(event["run"] for event in events)


class RehearsalOnTheFakeClientTestCase(FileWaitingTestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(root)
        self.state = self.machine.state_home / "brigade"
        self.store = root / "forge"
        self.remote = self.store / "remote.git"
        self.tools = root / "tools"
        self.machine.install_awawa(self)
        self.install_tools()
        self.machine.run_init()
        self.prepare_sandbox(root / "projects" / "shop")
        self.prepare_client(root / "recordings", root / "plays")
        self.register_sandbox()

    def tearDown(self):
        for record in sorted((self.state / "runs").glob("*/run.json")):
            self.wait_for_file(record.parent / "result.json")
        self.root.cleanup()

    def describe_environment(self) -> dict:
        return {**self.machine.describe_environment(), "PATH": f"{self.tools}{os.pathsep}{self.machine.search_path}"}

    def install_tools(self) -> None:
        install_executable(self.tools / "gh", f'#!/bin/sh\nexec "{sys.executable}" "{FORGE}" "{self.store}" "$@"\n')
        install_executable(self.tools / "brigade", f'#!/bin/sh\nexec "{sys.executable}" "{CLONE_ENTRY_POINT}" "$@"\n')

    def prepare_sandbox(self, path: Path) -> None:
        self.project = TemporaryProject(path, self.machine.describe_environment())
        self.project.run_git("init", "--quiet", "--bare", "--initial-branch=main", str(self.remote))
        self.project.write("corpus/_schema.awawa", SANDBOX_SCHEMA)
        self.project.write("corpus/tasks.awawa", SANDBOX_TASKS)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "the corpus of the sandbox")
        self.project.run_git("config", f"url.{self.remote}.insteadOf", REMOTE_URL)
        self.project.run_git("remote", "add", "origin", REMOTE_URL)
        self.project.run_git("push", "--quiet", "--set-upstream", "origin", "main")
        self.project.run_git("remote", "set-head", "origin", "main")

    def prepare_client(self, recordings: Path, plays: Path) -> None:
        recordings.mkdir()
        for role in ("planner", "builder", "reviewer", "reporter"):
            (recordings / f"{role}.json").write_text(json.dumps(DONE_RESULT))
        install_executable(plays / "planner", PLANNER_PLAY)
        install_executable(plays / "builder", BUILDER_PLAY)
        install_executable(plays / "reviewer", REVIEWER_PLAY)
        self.machine.write_configuration(
            f'client = "fake"\n{FORGE_ACCOUNTS}'
            f'[clients.fake]\nrecordings = "{recordings}"\nplays = "{plays}"\n{COUNTING_CLIENT}'
        )

    def register_sandbox(self) -> None:
        self.run_brigade("project", "add", str(self.project.path), "--acceptance", "true")
        projects = self.machine.corpus / "projects.awawa"
        projects.write_text(projects.read_text().replace('\tFORGE "none"\n', '\tFORGE "github"\n\tCHECK_RUNS none\n'))

    def run_brigade(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, *arguments, environment=self.describe_environment())

    def read_events(self, name: str) -> list:
        lines = "".join(path.read_text() for path in sorted((self.state / "ledger").glob("*.jsonl"))).splitlines()
        return [event for event in map(json.loads, lines) if event["event"] == name]

    def is_wave_integrated(self) -> bool:
        merged = [event for event in self.read_events("task.state") if event["state"] == "merged"]
        return len(merged) == 3 and bool(self.read_events("wave.pr_opened"))

    def tick_until_the_wave_is_integrated(self) -> None:
        deadline = time.monotonic() + REHEARSAL_WAIT_S
        while not self.is_wave_integrated():
            if time.monotonic() > deadline:
                self.fail(f"the wave was never integrated: {self.run_brigade('tick', '--dry-run').stdout}")
            completed = self.run_brigade("tick", "--once")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            time.sleep(TICK_INTERVAL_S)

    def read_pull_request(self, number: int) -> dict:
        return json.loads((self.store / "pulls" / f"{number}.json").read_text())

    def list_finished_runs(self) -> list[str]:
        records = sorted((self.state / "runs").glob("*/run.json"))
        for record in records:
            self.wait_for_file(record.parent / "result.json")
        return [record.parent.name for record in records]


class BrigadeRehearsalOfAThreeTaskWaveOnTheFakeClientTest(RehearsalOnTheFakeClientTestCase):
    def setUp(self):
        super().setUp()
        self.run_brigade("request", "new", "shop", "Let the customer empty the cart")
        self.tick_until_the_wave_is_integrated()

    def test_should_merge_the_three_tasks_into_the_branch_of_the_wave(self):
        # Act
        merged = list_merged_tasks(self.read_events("task.state"))

        # Assert
        self.assertEqual(merged, ["S1", "S2", "S3"])

    def test_should_open_the_integration_pull_request_wave_pr_opened_names(self):
        # Arrange
        opened = self.read_events("wave.pr_opened")[0]

        # Act
        pull_request = self.read_pull_request(opened["pr"])

        # Assert
        self.assertEqual(opened["wave"], "shop_w1")
        self.assertEqual(pull_request["headRefName"], "integration/shop_w1")
        self.assertEqual(pull_request["baseRefName"], "main")

    def test_should_record_every_run_in_the_ledger(self):
        # Arrange
        runs = self.list_finished_runs()

        # Act
        recorded = list_runs(self.read_events("run.finished"))

        # Assert
        self.assertEqual(recorded, runs)
