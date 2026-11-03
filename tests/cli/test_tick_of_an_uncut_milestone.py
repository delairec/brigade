import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY

from tests.cli.read_ledger_events import read_ledger_events
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import PINNED_COMMIT_DATES, TemporaryProject

PROJECT_SCHEMA = (
    "SCHEMA TASK\n"
    '\tDESC "a change delivered by one pull request"\n'
    "\tFIELD TITLE string\n\t\tREQUIRED\n"
    "\tFIELD STATUS todo|implemented\n\t\tREQUIRED\n"
    "\tFIELD MILESTONE @MILESTONE\n"
    "\n"
    "SCHEMA MILESTONE\n"
    '\tDESC "the tasks planned for one request"\n'
    "\tFIELD TITLE string\n\t\tREQUIRED\n"
    "\tFIELD STATUS active|reached\n\t\tREQUIRED\n"
)
RATIFIED_TASK = 'TASK S1\n\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
ACTIVE_MILESTONE = 'MILESTONE M1\n\tTITLE "Empty cart"\n\tSTATUS active\n'
BRANCH_OF_M1_CUT = {
    "schema_version": 1,
    "ts": ANY,
    "event": "milestone.branch_cut",
    "project": "shop",
    "milestone": "M1",
    "branch": "integration/empty-cart",
    "login": None,
}
WAVE_OF_S1_STARTED = {
    "schema_version": 2,
    "ts": ANY,
    "event": "wave.started",
    "wave": "shop_w1",
    "project": "shop",
    "branch": "integration/shop_w1",
    "tasks": ["S1"],
}


class TickOfARatifiedTaskWhoseMilestoneHasNoBranchTest(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.machine = TemporaryMachine(root)
        self.machine.install_awawa(self)
        self.machine.run_init()
        self.machine.pause_the_built_in_studies_of_shop()
        self.project = TemporaryProject(
            root / "projects" / "shop", {**self.machine.describe_environment(), **PINNED_COMMIT_DATES}
        )
        self.project.write("corpus/_schema.awawa", PROJECT_SCHEMA)
        self.project.write("corpus/tasks.awawa", RATIFIED_TASK)
        self.project.write("corpus/milestones.awawa", ACTIVE_MILESTONE)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "the plan of M1")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(self.project.path))

    def test_should_cut_the_branch_of_the_milestone_before_the_wave_starts(self):
        # Act
        self.machine.run_brigade(CLONE_ENTRY_POINT, "tick", "--once")

        # Assert
        events = read_ledger_events(self.machine.state_home / "brigade" / "ledger")
        self.assertEqual(events[:2], [BRANCH_OF_M1_CUT, WAVE_OF_S1_STARTED])
