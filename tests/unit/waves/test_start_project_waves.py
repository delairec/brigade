import unittest

from brigade.errors import BrigadeError
from brigade.system.parse_configuration import Configuration
from brigade.waves.start_project_wave import WaveStart
from brigade.waves.start_project_waves import start_project_waves
from tests.unit.commands.command_runtime import write_ledger
from tests.unit.select_argvs_opening_on import select_argvs_opening_on
from tests.unit.waves.test_start_project_wave import (
    BRANCH_NOT_FOUND,
    CUT_OF_M9,
    EVERY_STARTABLE_TASK,
    GIT_BRANCH,
    MAIN_SHA,
    MILESTONE_BRANCH,
    MILESTONE_SHA,
    NO_INCOMING_REFERENCE,
    OPEN_WAVE,
    TASKS_AT_THE_MILESTONE_BRANCH,
    StartProjectWaveTestCase,
)

TASKS_AT_MAIN = {
    "S7": (("STATUS", "todo"),),
    "S10": (("STATUS", "todo"),),
    "S20": (("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M9")),
    "S21": (("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M9"), ("AFTER", "@TASK.S20")),
    "S30": (("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M10")),
}
M9_ACTIVE = {"entities": [{"type": "MILESTONE", "name": "M9"}]}
ONLY_TASKS_IN_AN_OPEN_WAVE = {"S7": (("STATUS", "todo"),)}
WAVE_OF_M9 = {"wave": "shop_w2", "project": "shop", "branch": "integration/shop_w2", "tasks": ["S21"]}
WAVE_OF_NO_MILESTONE = {"wave": "shop_w3", "project": "shop", "branch": "integration/shop_w3", "tasks": ["S10"]}
FORGE_ENVIRONMENT = {"GH_TOKEN": "token-of-the-cli-slot"}


def _read_forge_environment(slot: str) -> dict:
    return FORGE_ENVIRONMENT


def _read_login() -> str:
    return "octo-bot"


class StartProjectWavesTestCase(StartProjectWaveTestCase):
    def setUp(self):
        super().setUp()
        write_ledger(self.root, [OPEN_WAVE, CUT_OF_M9])
        self.answer_local_branch("shop_w1", 0)
        self.main_tree = self.answer_tree("main", MAIN_SHA, TASKS_AT_MAIN)
        milestone_tree = self.answer_tree(MILESTONE_BRANCH, MILESTONE_SHA, TASKS_AT_THE_MILESTONE_BRANCH)
        self.processes.answer_json(
            ("awawa", "status", "MILESTONE", "--where", "STATUS==active", "--json", str(self.main_tree)), M9_ACTIVE
        )
        for tree in (self.main_tree, milestone_tree):
            self.processes.answer_entity(tree, "MILESTONE", "M9", (("TITLE", "Milestone integration branch"),))
        self.processes.answer(("git", "branch", "--quiet", "integration/shop_w2", MILESTONE_BRANCH))
        self.answer_local_branch("shop_w3", BRANCH_NOT_FOUND)
        self.processes.answer(("git", "branch", "--quiet", "integration/shop_w3", "main"))

    def answer_tree(self, ref: str, sha: str, tasks: dict):
        tree = self.root / "cache" / "refs" / "shop" / sha
        tree.mkdir(parents=True, exist_ok=True)
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}"), stdout=f"{sha}\n"
        )
        self.processes.answer_entities(tree, "TASK", tasks)
        for task in tasks:
            self.processes.answer_json(("awawa", "refs", f"@TASK.{task}", "--json", str(tree)), NO_INCOMING_REFERENCE)
        return tree

    def start_waves(self, tasks: tuple[str, ...]) -> tuple[dict, ...]:
        start = WaveStart(
            project="shop",
            tasks=tasks,
            configuration=Configuration(),
            read_environment=_read_forge_environment,
            read_login=_read_login,
        )
        return start_project_waves(self.runtime, start)


class StartProjectWavesOfTheCandidatesTest(StartProjectWavesTestCase):
    def test_should_start_one_wave_per_milestone_with_a_candidate_then_one_of_the_tasks_naming_none(self):
        # Act
        started = self.start_waves(EVERY_STARTABLE_TASK)

        # Assert
        self.assertEqual(started, (WAVE_OF_M9, WAVE_OF_NO_MILESTONE))

    def test_should_cut_the_wave_of_the_tasks_naming_no_milestone_from_the_main_branch(self):
        # Act
        self.start_waves(EVERY_STARTABLE_TASK)

        # Assert
        self.assertEqual(
            select_argvs_opening_on(self.processes.list_argvs(), GIT_BRANCH),
            [
                ("git", "branch", "--quiet", "integration/shop_w2", MILESTONE_BRANCH),
                ("git", "branch", "--quiet", "integration/shop_w2", MILESTONE_BRANCH),
                ("git", "branch", "--quiet", "integration/shop_w3", "main"),
            ],
        )

    def test_should_refuse_a_project_with_no_candidate(self):
        # Arrange
        self.answer_tree("main", MAIN_SHA, ONLY_TASKS_IN_AN_OPEN_WAVE)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            self.start_waves(EVERY_STARTABLE_TASK)

        # Assert
        self.assertEqual(str(raised.exception), "@PROJECT.shop has no task to start")


class StartProjectWavesOfNamedTasksTest(StartProjectWavesTestCase):
    def test_should_read_the_named_tasks_on_the_branch_of_their_milestone(self):
        # Act
        started = self.start_waves(("S21",))

        # Assert
        self.assertEqual(started, (WAVE_OF_M9,))

    def test_should_name_a_task_undefined_at_the_main_branch(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            self.start_waves(("S99",))

        # Assert
        self.assertEqual(str(raised.exception), "@TASK.S99 is not defined in the corpus of @PROJECT.shop")

    def test_should_name_a_task_undefined_at_the_main_branch_among_tasks_of_a_milestone(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            self.start_waves(("S99", "S21"))

        # Assert
        self.assertEqual(str(raised.exception), "@TASK.S99 is not defined in the corpus of @PROJECT.shop")

    def test_should_refuse_named_tasks_of_two_milestones_or_of_one_milestone_and_none_before_any_write(self):
        for tasks, expected_message in [
            (
                ("S10", "S21"),
                (
                    "@TASK.S10 names no milestone, @TASK.S21 names @MILESTONE.M9:"
                    " a wave takes the tasks of one milestone or tasks naming none"
                ),
            ),
            (
                ("S21", "S30"),
                (
                    "@TASK.S21 names @MILESTONE.M9, @TASK.S30 names @MILESTONE.M10:"
                    " a wave takes the tasks of one milestone or tasks naming none"
                ),
            ),
        ]:
            with self.subTest(tasks=tasks):
                # Act
                with self.assertRaises(BrigadeError) as raised:
                    self.start_waves(tasks)

                # Assert
                self.assertEqual(str(raised.exception), expected_message)
                self.assertEqual(self.read_events(), [OPEN_WAVE, CUT_OF_M9])


if __name__ == "__main__":
    unittest.main()
