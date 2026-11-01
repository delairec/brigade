import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import ProcessRequest
from brigade.waves.read_project_tasks import ProjectTasksReading, read_project_tasks
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.select_requests_opening_on import select_requests_opening_on

REPOSITORY = "/srv/shop"
MAIN_SHA = "4f1c2a9"
MILESTONE_SHA = "7d3e1b0"
MILESTONE_BRANCH = "integration/milestone-integration-branch"
FORGE_ENVIRONMENT = {"GH_TOKEN": "token-of-the-cli-slot"}
LS_REMOTE_OF_THE_MILESTONE_BRANCH = (
    "git",
    "ls-remote",
    "--quiet",
    "--exit-code",
    "--heads",
    "origin",
    f"refs/heads/{MILESTONE_BRANCH}",
)
REMOTE_BRANCH_NOT_FOUND = 2
CUT_OF_M9 = LedgerEntry(
    instant=datetime(2026, 10, 29, 9, 0, tzinfo=UTC),
    event=MilestoneBranchCut(project="shop", milestone="M9", branch=MILESTONE_BRANCH, login=None),
)
NO_EVENT = ()
TASKS_AT_MAIN = {"S20": (("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M9")), "S7": (("STATUS", "todo"),)}
TASKS_AT_THE_MILESTONE_BRANCH = {
    "S20": (("STATUS", "implemented"), ("MILESTONE", "@MILESTONE.M9")),
    "S21": (("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M9")),
}


def _read_forge_environment(slot: str) -> dict:
    return FORGE_ENVIRONMENT


class ReadProjectTasksTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.processes = ScriptedProcesses()
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
        self.main_tree = self.answer_tree("main", MAIN_SHA, TASKS_AT_MAIN)
        self.milestone_tree = self.answer_tree(MILESTONE_BRANCH, MILESTONE_SHA, TASKS_AT_THE_MILESTONE_BRANCH)
        self.forge = "none"

    def answer_tree(self, ref: str, sha: str, tasks: dict) -> Path:
        tree = self.root / "cache" / "refs" / "shop" / sha
        tree.mkdir(parents=True)
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}"), stdout=f"{sha}\n"
        )
        self.processes.answer_entities(tree, "TASK", tasks)
        return tree

    def read(self, milestone: str | None, entries: tuple[LedgerEntry, ...]):
        self.processes.answer_entities(
            self.root / "config", "PROJECT", {"shop": (("PATH", REPOSITORY), ("MAIN", "main"), ("FORGE", self.forge))}
        )
        project = Entity(
            name="shop",
            fields=(
                EntityField(name="PATH", value=REPOSITORY),
                EntityField(name="MAIN", value="main"),
                EntityField(name="FORGE", value=self.forge),
            ),
        )
        reading = ProjectTasksReading(
            configuration=Configuration(),
            project=project,
            read_environment=_read_forge_environment,
            entries=entries,
        )
        return read_project_tasks(self.runtime, reading, milestone)


class ReadProjectTasksOfAMilestoneTest(ReadProjectTasksTestCase):
    def test_should_read_the_tasks_of_a_milestone_at_the_branch_the_ledger_records(self):
        # Act
        tasks = self.read("M9", (CUT_OF_M9,))

        # Assert
        self.assertEqual(tasks.root, self.milestone_tree)
        self.assertEqual(tasks.implemented, frozenset({"S20"}))
        self.assertEqual(tasks.milestone, "M9")

    def test_should_read_the_tasks_of_a_milestone_whose_branch_is_not_cut_at_the_main_branch(self):
        # Act
        tasks = self.read("M9", NO_EVENT)

        # Assert
        self.assertEqual(tasks.root, self.main_tree)

    def test_should_read_the_tasks_naming_no_milestone_at_the_main_branch(self):
        # Act
        tasks = self.read(None, (CUT_OF_M9,))

        # Assert
        self.assertEqual(tasks.root, self.main_tree)

    def test_should_fetch_the_branch_of_the_milestone_from_the_github_forge(self):
        # Arrange
        self.forge = "github"
        self.answer_tree(f"origin/{MILESTONE_BRANCH}", "c0ffee1", TASKS_AT_THE_MILESTONE_BRANCH)
        self.processes.answer(LS_REMOTE_OF_THE_MILESTONE_BRANCH)
        self.processes.answer(("git", "fetch", "--quiet", "origin", MILESTONE_BRANCH))

        # Act
        self.read("M9", (CUT_OF_M9,))

        # Assert
        self.assertEqual(
            select_requests_opening_on(self.processes.requests, ("git", "fetch")),
            [
                ProcessRequest(
                    argv=("git", "fetch", "--quiet", "origin", MILESTONE_BRANCH),
                    cwd=REPOSITORY,
                    timeout_s=120.0,
                    environment=FORGE_ENVIRONMENT,
                )
            ],
        )

    def test_should_read_the_tasks_of_a_milestone_whose_branch_the_forge_deleted_at_the_main_branch_of_the_forge(
        self,
    ):
        # Arrange
        self.forge = "github"
        main_of_the_forge = self.answer_tree("origin/main", "b0a7e55", TASKS_AT_MAIN)
        self.processes.answer(LS_REMOTE_OF_THE_MILESTONE_BRANCH, exit_code=REMOTE_BRANCH_NOT_FOUND)
        self.processes.answer(
            ("git", "fetch", "--quiet", "origin", MILESTONE_BRANCH),
            exit_code=128,
            stderr=f"fatal: couldn't find remote ref {MILESTONE_BRANCH}",
        )
        self.processes.answer(("git", "fetch", "--quiet", "origin", "main"))

        # Act
        tasks = self.read("M9", (CUT_OF_M9,))

        # Assert
        self.assertEqual(tasks.root, main_of_the_forge)


if __name__ == "__main__":
    unittest.main()
