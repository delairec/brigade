import json
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import ProcessRequest
from brigade.waves.start_project_wave import WaveStart, start_project_wave
from tests.unit.commands.command_runtime import write_ledger, write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.select_argvs_opening_on import select_argvs_opening_on
from tests.unit.select_requests_opening_on import select_requests_opening_on

GIT_BRANCH = ("git", "branch")
GIT_FETCH = ("git", "fetch")
GIT_PUSH = ("git", "push")

REPOSITORY = "/srv/shop"
MAIN_SHA = "4f1c2a9"
FORGE_MAIN_SHA = "9b0d3e7"
BRANCH_NOT_FOUND = 1
REMOTE_BRANCH_NOT_FOUND = 2
FORGE_ENVIRONMENT = {"GH_TOKEN": "token-of-the-build-slot"}
TASKS = {
    "S2": (("STATUS", "implemented"),),
    "S3": (("STATUS", "todo"), ("AFTER", "@TASK.S2")),
    "S4": (("STATUS", "todo"), ("AFTER", "@TASK.S3")),
    "S5": (("STATUS", "todo"), ("AFTER", "@TASK.S6")),
    "S6": (("STATUS", "todo"),),
    "S7": (("STATUS", "todo"),),
    "S10": (("STATUS", "todo"),),
    "Cleanup": (("STATUS", "todo"),),
}
NO_INCOMING_REFERENCE = {"incoming": []}
BLOCKING_QUESTION = {
    "incoming": [
        {"from": {"type": "OPEN_QUESTION", "name": "KeepDuration", "status": "open"}, "field_path": ["BLOCKS"]}
    ]
}
QUESTION_SCHEMA = {
    "fields": [
        {"name": "FIELD", "atoms": ["BLOCKS", "@TASK"], "fields": [{"name": "CONVERSE", "atoms": ["BLOCKED_BY"]}]}
    ]
}
OPEN_WAVE = {
    "schema_version": 2,
    "ts": "2026-10-13T09:00:00Z",
    "event": "wave.started",
    "wave": "shop_w1",
    "project": "shop",
    "branch": "integration/shop_w1",
    "tasks": ["S7"],
}
EVERY_STARTABLE_TASK = ()
NO_MILESTONE = None
MILESTONE_SHA = "7d3e1b0"
MILESTONE_BRANCH = "integration/milestone-integration-branch"
TASKS_OF_A_MILESTONE = {
    "S7": (("STATUS", "todo"),),
    "S20": (("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M9")),
    "S21": (("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M9")),
}
TASKS_AT_THE_MILESTONE_BRANCH = {
    "S20": (("STATUS", "implemented"), ("MILESTONE", "@MILESTONE.M9")),
    "S21": (("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M9"), ("AFTER", "@TASK.S20")),
}
CUT_OF_M9 = {
    "schema_version": 1,
    "ts": "2026-10-14T09:00:00Z",
    "event": "milestone.branch_cut",
    "project": "shop",
    "milestone": "M9",
    "branch": MILESTONE_BRANCH,
    "login": None,
}


def _read_forge_environment(slot: str) -> dict:
    return FORGE_ENVIRONMENT


def _read_login() -> str:
    return "octo-bot"


class StartProjectWaveTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.processes = ScriptedProcesses()
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
        tree = self.root / "cache" / "refs" / "shop" / MAIN_SHA
        tree.mkdir(parents=True)
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "main^{commit}"), stdout=f"{MAIN_SHA}\n"
        )
        self.processes.answer_entities(tree, "TASK", TASKS)
        for task in TASKS:
            self.processes.answer_json(("awawa", "refs", f"@TASK.{task}", "--json", str(tree)), NO_INCOMING_REFERENCE)
        self.processes.answer_json(("awawa", "refs", "@TASK.S6", "--json", str(tree)), BLOCKING_QUESTION)
        self.processes.answer_json(("awawa", "show", "OPEN_QUESTION", "--json", str(tree)), QUESTION_SCHEMA)
        for wave in ("shop_w1", "shop_w2"):
            self.answer_local_branch(wave, BRANCH_NOT_FOUND)
            self.processes.answer(("git", "branch", "--quiet", f"integration/{wave}", "main"))
        write_ledger(self.root, [OPEN_WAVE])
        self.register_project("none")

    def register_project(self, forge: str) -> None:
        self.processes.answer_entities(
            self.root / "config", "PROJECT", {"shop": (("PATH", REPOSITORY), ("MAIN", "main"), ("FORGE", forge))}
        )

    def register_github_project(self) -> None:
        self.register_project("github")
        self.processes.answer(("git", "fetch", "--quiet", "origin", "main"))
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "origin/main^{commit}"),
            stdout=f"{MAIN_SHA}\n",
        )
        for wave in ("shop_w1", "shop_w2"):
            self.processes.answer(("git", "branch", "--quiet", f"integration/{wave}", "origin/main"))

    def answer_local_branch(self, wave: str, exit_code: int) -> None:
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", f"refs/heads/integration/{wave}"), exit_code=exit_code
        )

    def answer_remote_branch(self, wave: str, exit_code: int) -> None:
        argv = ("git", "ls-remote", "--quiet", "--exit-code", "--heads", "origin", f"refs/heads/integration/{wave}")
        self.processes.answer(argv, exit_code=exit_code)

    def start_wave(self, tasks: tuple[str, ...], milestone: str | None = NO_MILESTONE) -> dict:
        start = WaveStart(
            project="shop",
            tasks=tasks,
            configuration=Configuration(),
            read_environment=_read_forge_environment,
            read_login=_read_login,
        )
        return start_project_wave(self.runtime, start, milestone)

    def read_events(self) -> list[dict]:
        return list(
            map(json.loads, (self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8").splitlines())
        )


class StartProjectWaveOfTheStartableTasksTest(StartProjectWaveTestCase):
    def test_should_compose_the_wave_from_the_startable_tasks_in_the_order_of_their_number(self):
        # Act
        started = self.start_wave(EVERY_STARTABLE_TASK)

        # Assert
        self.assertEqual(
            started,
            {"wave": "shop_w2", "project": "shop", "branch": "integration/shop_w2", "tasks": ["S3", "S4", "S10"]},
        )

    def test_should_record_the_start_of_the_wave_in_the_ledger(self):
        # Act
        self.start_wave(EVERY_STARTABLE_TASK)

        # Assert
        self.assertEqual(
            self.read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-13T09:00:00Z",
                    "event": "wave.started",
                    "wave": "shop_w1",
                    "project": "shop",
                    "branch": "integration/shop_w1",
                    "tasks": ["S7"],
                },
                {
                    "schema_version": 2,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "wave.started",
                    "wave": "shop_w2",
                    "project": "shop",
                    "branch": "integration/shop_w2",
                    "tasks": ["S3", "S4", "S10"],
                },
            ],
        )

    def test_should_cut_the_branch_of_every_open_wave_missing_it_from_the_main_branch(self):
        # Act
        self.start_wave(EVERY_STARTABLE_TASK)

        # Assert
        self.assertEqual(
            select_argvs_opening_on(self.processes.list_argvs(), GIT_BRANCH),
            [
                ("git", "branch", "--quiet", "integration/shop_w1", "main"),
                ("git", "branch", "--quiet", "integration/shop_w2", "main"),
            ],
        )

    def test_should_leave_the_branch_of_an_open_wave_that_has_one(self):
        # Arrange
        self.answer_local_branch("shop_w1", 0)

        # Act
        self.start_wave(EVERY_STARTABLE_TASK)

        # Assert
        self.assertNotIn(("git", "branch", "--quiet", "integration/shop_w1", "main"), self.processes.list_argvs())

    def test_should_refuse_a_project_with_no_task_left_to_start(self):
        # Arrange
        self.start_wave(EVERY_STARTABLE_TASK)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            self.start_wave(EVERY_STARTABLE_TASK)

        # Assert
        self.assertEqual(str(raised.exception), "@PROJECT.shop has no task to start")


class StartProjectWaveOfNamedTasksTest(StartProjectWaveTestCase):
    def test_should_take_exactly_the_named_tasks_in_the_order_of_their_number(self):
        # Act
        started = self.start_wave(("S4", "S3"))

        # Assert
        self.assertEqual(started["tasks"], ["S3", "S4"])

    def test_should_refuse_a_task_before_any_write(self):
        for task, expected_message in [
            ("S7", "@TASK.S7 is in the open wave shop_w1"),
            ("Cleanup", "@TASK.Cleanup has no number in its name"),
            ("S4", "@TASK.S4 comes after @TASK.S3, neither implemented nor named"),
            ("S99", "@TASK.S99 is not defined in the corpus of @PROJECT.shop"),
        ]:
            with self.subTest(task=task):
                # Act
                with self.assertRaises(BrigadeError) as raised:
                    self.start_wave((task,))

                # Assert
                self.assertEqual(str(raised.exception), expected_message)
                self.assertEqual(
                    self.read_events(),
                    [
                        {
                            "schema_version": 2,
                            "ts": "2026-10-13T09:00:00Z",
                            "event": "wave.started",
                            "wave": "shop_w1",
                            "project": "shop",
                            "branch": "integration/shop_w1",
                            "tasks": ["S7"],
                        }
                    ],
                )


class StartProjectWaveOnABranchNoWaveStartedNamesTest(StartProjectWaveTestCase):
    def test_should_refuse_a_local_branch_of_the_name(self):
        # Arrange
        self.answer_local_branch("shop_w2", 0)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            self.start_wave(EVERY_STARTABLE_TASK)

        # Assert
        self.assertEqual(str(raised.exception), "the branch integration/shop_w2 exists and no wave.started names it")
        self.assertEqual(
            self.read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-13T09:00:00Z",
                    "event": "wave.started",
                    "wave": "shop_w1",
                    "project": "shop",
                    "branch": "integration/shop_w1",
                    "tasks": ["S7"],
                }
            ],
        )

    def test_should_refuse_a_remote_branch_of_the_name_on_the_github_forge(self):
        # Arrange
        self.register_github_project()
        self.answer_remote_branch("shop_w2", 0)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            self.start_wave(EVERY_STARTABLE_TASK)

        # Assert
        self.assertEqual(str(raised.exception), "the branch integration/shop_w2 exists and no wave.started names it")


class StartProjectWaveOnTheGithubForgeTest(StartProjectWaveTestCase):
    def test_should_compose_the_wave_from_the_main_branch_of_the_forge(self):
        # Arrange
        self.register_github_project()
        forge_tree = self.root / "cache" / "refs" / "shop" / FORGE_MAIN_SHA
        forge_tree.mkdir(parents=True)
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "origin/main^{commit}"),
            stdout=f"{FORGE_MAIN_SHA}\n",
        )
        self.processes.answer_entities(forge_tree, "TASK", {"S11": (("STATUS", "todo"),)})
        self.processes.answer_json(("awawa", "refs", "@TASK.S11", "--json", str(forge_tree)), NO_INCOMING_REFERENCE)
        self.answer_remote_branch("shop_w2", REMOTE_BRANCH_NOT_FOUND)
        self.processes.answer(("git", "push", "--quiet", "origin", "integration/shop_w2"))
        self.answer_local_branch("shop_w1", 0)
        self.answer_remote_branch("shop_w1", 0)

        # Act
        started = self.start_wave(EVERY_STARTABLE_TASK)

        # Assert
        self.assertEqual(started["tasks"], ["S11"])

    def test_should_fetch_the_main_branch_with_the_environment_of_the_forge(self):
        # Arrange
        self.register_github_project()
        self.answer_local_branch("shop_w1", 0)
        self.answer_remote_branch("shop_w1", 0)
        self.answer_remote_branch("shop_w2", REMOTE_BRANCH_NOT_FOUND)
        self.processes.answer(("git", "push", "--quiet", "origin", "integration/shop_w2"))

        # Act
        self.start_wave(EVERY_STARTABLE_TASK)

        # Assert
        self.assertEqual(
            select_requests_opening_on(self.processes.requests, GIT_FETCH),
            [
                ProcessRequest(
                    argv=("git", "fetch", "--quiet", "origin", "main"),
                    cwd=REPOSITORY,
                    timeout_s=120.0,
                    environment=FORGE_ENVIRONMENT,
                ),
                ProcessRequest(
                    argv=("git", "fetch", "--quiet", "origin", "main"),
                    cwd=REPOSITORY,
                    timeout_s=120.0,
                    environment=FORGE_ENVIRONMENT,
                ),
            ],
        )

    def test_should_push_the_integration_branch_with_the_environment_of_the_forge(self):
        # Arrange
        self.register_github_project()
        for wave in ("shop_w1", "shop_w2"):
            self.answer_remote_branch(wave, REMOTE_BRANCH_NOT_FOUND)
            self.processes.answer(("git", "push", "--quiet", "origin", f"integration/{wave}"))

        # Act
        self.start_wave(EVERY_STARTABLE_TASK)

        # Assert
        self.assertEqual(
            select_requests_opening_on(self.processes.requests, GIT_PUSH),
            [
                ProcessRequest(
                    argv=("git", "push", "--quiet", "origin", "integration/shop_w1"),
                    cwd=REPOSITORY,
                    timeout_s=120.0,
                    environment=FORGE_ENVIRONMENT,
                ),
                ProcessRequest(
                    argv=("git", "push", "--quiet", "origin", "integration/shop_w2"),
                    cwd=REPOSITORY,
                    timeout_s=120.0,
                    environment=FORGE_ENVIRONMENT,
                ),
            ],
        )

    def test_should_push_the_branch_of_an_open_wave_the_remote_lacks_without_cutting_it_again(self):
        # Arrange
        self.register_github_project()
        self.answer_local_branch("shop_w1", 0)
        for wave in ("shop_w1", "shop_w2"):
            self.answer_remote_branch(wave, REMOTE_BRANCH_NOT_FOUND)
            self.processes.answer(("git", "push", "--quiet", "origin", f"integration/{wave}"))

        # Act
        self.start_wave(EVERY_STARTABLE_TASK)

        # Assert
        self.assertEqual(
            select_argvs_opening_on(self.processes.list_argvs(), GIT_BRANCH, GIT_PUSH),
            [
                ("git", "push", "--quiet", "origin", "integration/shop_w1"),
                ("git", "branch", "--quiet", "integration/shop_w2", "origin/main"),
                ("git", "push", "--quiet", "origin", "integration/shop_w2"),
            ],
        )

    def test_should_leave_the_branch_of_an_open_wave_the_remote_holds(self):
        # Arrange
        self.register_github_project()
        self.answer_local_branch("shop_w1", 0)
        self.answer_remote_branch("shop_w1", 0)
        self.answer_remote_branch("shop_w2", REMOTE_BRANCH_NOT_FOUND)
        self.processes.answer(("git", "push", "--quiet", "origin", "integration/shop_w2"))

        # Act
        self.start_wave(EVERY_STARTABLE_TASK)

        # Assert
        self.assertNotIn(("git", "push", "--quiet", "origin", "integration/shop_w1"), self.processes.list_argvs())


class StartProjectWaveOfTheTasksOfAMilestoneTest(StartProjectWaveTestCase):
    def setUp(self):
        super().setUp()
        tree = self.root / "cache" / "refs" / "shop" / MAIN_SHA
        self.processes.answer_entities(tree, "TASK", TASKS_OF_A_MILESTONE)
        for task in TASKS_OF_A_MILESTONE:
            self.processes.answer_json(("awawa", "refs", f"@TASK.{task}", "--json", str(tree)), NO_INCOMING_REFERENCE)
        self.processes.answer_entity(tree, "MILESTONE", "M9", (("TITLE", "Milestone integration branch"),))
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", f"refs/heads/{MILESTONE_BRANCH}"), exit_code=BRANCH_NOT_FOUND
        )
        self.processes.answer(("git", "branch", "--quiet", MILESTONE_BRANCH, "main"))
        self.processes.answer(("git", "branch", "--quiet", "integration/shop_w2", MILESTONE_BRANCH))
        milestone_tree = self.root / "cache" / "refs" / "shop" / MILESTONE_SHA
        milestone_tree.mkdir(parents=True)
        for ref in (MILESTONE_BRANCH, f"origin/{MILESTONE_BRANCH}"):
            self.processes.answer(
                ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}"),
                stdout=f"{MILESTONE_SHA}\n",
            )
        self.processes.answer_entities(milestone_tree, "TASK", TASKS_AT_THE_MILESTONE_BRANCH)
        for task in TASKS_AT_THE_MILESTONE_BRANCH:
            argv = ("awawa", "refs", f"@TASK.{task}", "--json", str(milestone_tree))
            self.processes.answer_json(argv, NO_INCOMING_REFERENCE)
        self.processes.answer_entity(milestone_tree, "MILESTONE", "M9", (("TITLE", "Milestone integration branch"),))

    def test_should_compose_the_wave_of_a_milestone_from_the_tasks_at_the_branch_the_ledger_records(self):
        # Arrange
        write_ledger(self.root, [OPEN_WAVE, CUT_OF_M9])
        self.answer_local_branch("shop_w1", 0)

        # Act
        started = self.start_wave(EVERY_STARTABLE_TASK, "M9")

        # Assert
        self.assertEqual(started["tasks"], ["S21"])

    def test_should_cut_the_branch_of_the_milestone_from_the_main_branch_then_the_wave_branch_from_it(self):
        # Act
        self.start_wave(("S20", "S21"), "M9")

        # Assert
        self.assertEqual(
            select_argvs_opening_on(self.processes.list_argvs(), GIT_BRANCH),
            [
                ("git", "branch", "--quiet", "integration/shop_w1", "main"),
                ("git", "branch", "--quiet", MILESTONE_BRANCH, "main"),
                ("git", "branch", "--quiet", "integration/shop_w2", MILESTONE_BRANCH),
            ],
        )

    def test_should_record_the_cut_of_the_branch_of_the_milestone(self):
        # Act
        self.start_wave(("S20", "S21"), "M9")

        # Assert
        self.assertEqual(
            self.read_events()[-1],
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "milestone.branch_cut",
                "project": "shop",
                "milestone": "M9",
                "branch": MILESTONE_BRANCH,
                "login": None,
            },
        )

    def test_should_cut_the_branch_of_the_next_wave_from_the_branch_the_ledger_records(self):
        # Arrange
        write_ledger(self.root, [OPEN_WAVE, CUT_OF_M9])
        self.answer_local_branch("shop_w1", 0)

        # Act
        self.start_wave(("S21",), "M9")

        # Assert
        self.assertEqual(
            select_argvs_opening_on(self.processes.list_argvs(), GIT_BRANCH),
            [("git", "branch", "--quiet", "integration/shop_w2", MILESTONE_BRANCH)],
        )

    def test_should_refuse_the_wave_naming_the_milestone_and_the_branch_the_clone_holds_unrecorded(self):
        # Arrange
        self.processes.answer(("git", "rev-parse", "--verify", "--quiet", f"refs/heads/{MILESTONE_BRANCH}"))

        # Act
        with self.assertRaises(BrigadeError) as raised:
            self.start_wave(("S20",), "M9")

        # Assert
        self.assertEqual(
            str(raised.exception),
            f"@MILESTONE.M9: the branch {MILESTONE_BRANCH} exists and no milestone.branch_cut records it",
        )

    def test_should_cut_the_wave_branch_from_the_milestone_branch_of_the_forge(self):
        # Arrange
        self.register_github_project()
        write_ledger(self.root, [OPEN_WAVE, CUT_OF_M9])
        self.answer_local_branch("shop_w1", 0)
        self.answer_remote_branch("shop_w1", 0)
        self.answer_remote_branch("shop_w2", REMOTE_BRANCH_NOT_FOUND)
        self.processes.answer(("git", "fetch", "--quiet", "origin", MILESTONE_BRANCH))
        self.processes.answer(("git", "branch", "--quiet", "integration/shop_w2", f"origin/{MILESTONE_BRANCH}"))
        self.processes.answer(("git", "push", "--quiet", "origin", "integration/shop_w2"))

        # Act
        self.start_wave(("S21",), "M9")

        # Assert
        self.assertEqual(
            select_argvs_opening_on(self.processes.list_argvs(), GIT_BRANCH),
            [("git", "branch", "--quiet", "integration/shop_w2", f"origin/{MILESTONE_BRANCH}")],
        )


if __name__ == "__main__":
    unittest.main()
