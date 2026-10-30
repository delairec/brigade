import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import ANY

from brigade.commands.wave_start import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_corpus_double, write_operational_corpus
from tests.unit.commands.create_plugin_resolver import create_plugin_resolver
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.waves.test_start_project_wave import (
    CUT_OF_M9,
    MAIN_SHA,
    MILESTONE_BRANCH,
    NO_INCOMING_REFERENCE,
    REMOTE_BRANCH_NOT_FOUND,
    TASKS_OF_A_MILESTONE,
    StartProjectWaveTestCase,
)

NO_PROJECTS = {"PROJECT": {}}


class WaveStartTextTest(unittest.TestCase):
    def test_should_name_each_wave_its_project_its_branch_and_its_tasks(self):
        # Arrange
        document = {
            "schema_version": 2,
            "waves": [
                {"wave": "tidepool_w16", "project": "tidepool", "branch": "integration/tidepool_w16", "tasks": ["S3"]},
                {"wave": "tidepool_w17", "project": "tidepool", "branch": "integration/tidepool_w17", "tasks": ["S6"]},
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "wave tidepool_w16 of @PROJECT.tidepool on integration/tidepool_w16: S3\n"
            "wave tidepool_w17 of @PROJECT.tidepool on integration/tidepool_w17: S6",
        )


class WaveStartExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 2, "waves": []})

        # Assert
        self.assertEqual(exit_code, 0)


class WaveStartRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(project="tidepool", tasks=["S3"])

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class WaveStartOfNamedTasksTest(StartProjectWaveTestCase):
    def test_should_start_the_wave_on_the_tasks_the_command_line_names(self):
        # Arrange
        options = Namespace(project="shop", tasks=["S10"])

        # Act
        document = COMMAND.run(options, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 2,
                "waves": [{"wave": "shop_w2", "project": "shop", "branch": "integration/shop_w2", "tasks": ["S10"]}],
            },
        )


class WaveStartCuttingTheBranchOfAMilestoneOnTheGithubForgeTest(StartProjectWaveTestCase):
    def setUp(self):
        super().setUp()
        forge = ForgeDouble({"describe_account": lambda request: {"schema_version": 1, "login": "shop-cli"}})
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=self.processes,
            resolve_plugin=create_plugin_resolver({("forge", "github"): forge}),
        )
        self.register_github_project()
        tree = self.root / "cache" / "refs" / "shop" / MAIN_SHA
        self.processes.answer_entities(tree, "TASK", TASKS_OF_A_MILESTONE)
        for task in TASKS_OF_A_MILESTONE:
            self.processes.answer_json(("awawa", "refs", f"@TASK.{task}", "--json", str(tree)), NO_INCOMING_REFERENCE)
        self.processes.answer_entity(tree, "MILESTONE", "M9", (("TITLE", "Milestone integration branch"),))
        self.answer_local_branch("shop_w1", 0)
        self.answer_remote_branch("shop_w1", 0)
        self.answer_remote_branch("shop_w2", REMOTE_BRANCH_NOT_FOUND)
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", f"refs/heads/{MILESTONE_BRANCH}"), exit_code=1
        )
        self.processes.answer(
            ("git", "ls-remote", "--quiet", "--exit-code", "--heads", "origin", f"refs/heads/{MILESTONE_BRANCH}"),
            exit_code=REMOTE_BRANCH_NOT_FOUND,
        )
        self.processes.answer(("git", "branch", "--quiet", MILESTONE_BRANCH, "origin/main"))
        self.processes.answer(("git", "push", "--quiet", "origin", MILESTONE_BRANCH))
        self.processes.answer(("git", "fetch", "--quiet", "origin", MILESTONE_BRANCH))
        self.processes.answer(("git", "branch", "--quiet", "integration/shop_w2", f"origin/{MILESTONE_BRANCH}"))
        self.processes.answer(("git", "push", "--quiet", "origin", "integration/shop_w2"))

    def test_should_record_the_cut_of_the_branch_of_the_milestone_with_the_login_of_the_cli(self):
        # Act
        COMMAND.run(Namespace(project="shop", tasks=["S20"]), self.runtime)

        # Assert
        self.assertIn({**CUT_OF_M9, "ts": ANY, "login": "shop-cli"}, self.read_events())


class WaveStartOfAnUnknownProjectTest(unittest.TestCase):
    def test_should_refuse_a_project_not_registered(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        runtime = create_test_runtime(create_test_paths(root), run_process=create_corpus_double(NO_PROJECTS))
        every_startable_task = []

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(project="tidepool", tasks=every_startable_task), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "@PROJECT.tidepool is not registered")
