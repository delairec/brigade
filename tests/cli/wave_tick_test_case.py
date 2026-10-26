import json
import os
import tempfile
import unittest
from pathlib import Path

from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, FileWaitingTestCase
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import PINNED_COMMIT_DATES, TemporaryProject
from tests.cli.test_collect import install_executable

PROJECT_SCHEMA = (
    "SCHEMA TASK\n"
    '\tDESC "a change delivered by one pull request"\n'
    "\tFIELD TITLE string\n\t\tREQUIRED\n"
    "\tFIELD STATUS todo|implemented\n\t\tREQUIRED\n"
    "\tFIELD MILESTONE @MILESTONE\n"
    "\tFIELD AFTER @TASK\n\t\tREPEATABLE\n"
    "\n"
    "SCHEMA MILESTONE\n"
    '\tDESC "the tasks planned for one request"\n'
    "\tFIELD TITLE string\n\t\tREQUIRED\n"
    "\tFIELD STATUS planned|running\n\t\tREQUIRED\n"
    "\n"
    "SCHEMA OPEN_QUESTION\n"
    '\tDESC "a fact left undecided"\n'
    "\tFIELD STATUS open|closed\n\t\tREQUIRED\n"
    "\tFIELD BLOCKS @TASK\n\t\tREPEATABLE\n\t\tCONVERSE BLOCKED_BY\n"
    "\tWHEN STATUS closed\n\t\tGATE suppressed\n"
)
MAIN_TASKS = 'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n'
WAVE_TASKS = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\n'
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n\tAFTER @TASK.S2\n\n'
    'TASK S4\n\tTITLE "Confirm before emptying the cart"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
    "\tAFTER @TASK.S3\n\n"
    'TASK S5\n\tTITLE "Undo the emptying"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n\n'
    'TASK S6\n\tTITLE "Count the emptied carts"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
)
WAVE_MILESTONES = 'MILESTONE M1\n\tTITLE "Empty cart"\n\tSTATUS running\n'
WAVE_QUESTIONS = (
    "OPEN_QUESTION Undecided\n\tSTATUS open\n\tBLOCKS @TASK.S5\n\n"
    "OPEN_QUESTION Ruled\n\tSTATUS closed\n\tBLOCKS @TASK.S6\n"
)
WAVE_BRANCH = "integration/M1-empty-cart"
WAVE_EVENTS = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    f' "project": "shop", "branch": "{WAVE_BRANCH}", "tasks": ["S3", "S4", "S5", "S6"]}}\n'
    '{"schema_version": 1, "ts": "2026-10-13T10:00:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "queued"}\n'
    '{"schema_version": 1, "ts": "2026-10-13T10:30:00Z", "event": "task.state", "wave": "cafe_w1", "task": "S6",'
    ' "state": "running"}\n'
)
REPLACING_PROCEDURE = "---\ncapabilities: read, shell\nbudget: 40\n---\nDeliver the task another way.\n"
TOKENLESS_LOGIN = "octo-tokenless"
FAKE_GH = (
    "#!/bin/sh\n"
    'printf \'%s %s\\n\' "${{GH_TOKEN:-no GH_TOKEN}}" "$*" >> "{calls}"\n'
    'case "$1 $2" in\n'
    '  "auth token") if [ "$6" = "{tokenless}" ]; then exit 1; fi; printf \'token-of-%s\\n\' "$6" ;;\n'
    '  "pr list") answer="{pull_requests}/$(printf \'%s\' "$4" | tr / -)"\n'
    '    if [ -f "$answer.refused" ]; then echo "HTTP 502: Bad Gateway" >&2; exit 1; fi\n'
    '    if [ -f "$answer.json" ]; then cat "$answer.json"; else echo "[]"; fi ;;\n'
    '  "api repos/{{owner}}/{{repo}}/compare/"*) if [ -f "{pull_requests}/behind-by" ]; then\n'
    '    cat "{pull_requests}/behind-by"; else echo 0; fi ;;\n'
    "  *) exit 2 ;;\n"
    "esac\n"
)


class WaveTickTestCase(unittest.TestCase):
    setup_commands = ("touch setup-ran",)

    def run_tick(self, *options: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "tick", *options, environment=self.describe_environment())

    def read_events(self) -> list:
        lines = "".join(path.read_text() for path in sorted((self.state / "ledger").glob("*.jsonl"))).splitlines()
        return list(map(json.loads, lines))

    def describe_environment(self) -> dict:
        return {
            **self.machine.describe_environment(),
            **PINNED_COMMIT_DATES,
            "PATH": f"{self.tools}{os.pathsep}{self.machine.search_path}",
        }

    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.machine = TemporaryMachine(Path(self.root.name).resolve())
        self.state = self.machine.state_home / "brigade"
        root = Path(self.root.name).resolve()
        self.tools = root / "tools"
        self.gh_calls = root / "gh-calls"
        self.pull_requests = root / "pull-requests"
        self.pull_requests.mkdir()
        install_executable(
            self.tools / "gh",
            FAKE_GH.format(calls=self.gh_calls, pull_requests=self.pull_requests, tokenless=TOKENLESS_LOGIN),
        )
        self.machine.install_awawa(self)
        self.machine.run_init()
        self.machine.pause_the_built_in_triage()
        self.project = TemporaryProject(
            Path(self.root.name).resolve() / "projects" / "shop",
            {**self.machine.describe_environment(), **PINNED_COMMIT_DATES},
        )
        self.project.write("corpus/_schema.awawa", PROJECT_SCHEMA)
        self.project.write("corpus/tasks.awawa", MAIN_TASKS)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "the corpus")
        self.project.run_git("checkout", "--quiet", "-b", WAVE_BRANCH)
        self.project.write("corpus/tasks.awawa", WAVE_TASKS)
        self.project.write("corpus/milestones.awawa", WAVE_MILESTONES)
        self.project.write("corpus/questions.awawa", WAVE_QUESTIONS)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "the plan of M1")
        self.project.run_git("checkout", "--quiet", "main")
        self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "project",
            "add",
            str(self.project.path),
            *(argument for command in self.setup_commands for argument in ("--setup", command)),
        )
        (self.state / "ledger").mkdir(parents=True)
        (self.state / "ledger" / "2026-10.jsonl").write_text(WAVE_EVENTS)


class LaunchingTickTestCase(WaveTickTestCase, FileWaitingTestCase):
    def setUp(self):
        super().setUp()
        recordings = Path(self.root.name) / "recordings"
        recordings.mkdir()
        (recordings / "builder.json").write_text(json.dumps(DONE_RESULT))
        instructions = Path(self.root.name) / "instructions"
        (instructions / "procedures").mkdir(parents=True)
        (instructions / "procedures" / "deliver.md").write_text(REPLACING_PROCEDURE)
        self.configure(recordings, instructions)
        self.worktree = self.project.path / ".brigade" / "worktrees" / "S3"

    def configure(self, recordings: Path, instructions: Path, keys: str = "") -> None:
        self.machine.write_configuration(
            f'client = "fake"\ndocument = "markdown"\ninstructions = "{instructions}"\n{keys}'
            f'[clients.fake]\nrecordings = "{recordings}"\n{COUNTING_CLIENT}'
        )

    def tearDown(self):
        self.wait_for_the_runs()
        super().tearDown()

    def wait_for_the_runs(self) -> None:
        for record in self.read_run_records():
            self.wait_for_file(self.state / "runs" / record["run"] / "result.json")

    def read_run_records(self) -> list:
        return [json.loads(path.read_text()) for path in sorted((self.state / "runs").glob("*/run.json"))]
