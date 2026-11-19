import json
import sys
import tempfile
import unittest
from pathlib import Path

from brigade.dashboard.start_awawa_addon import start_awawa_addon
from brigade.errors import ToolNotFound
from brigade.system.start_piped_process import PipedProcessRequest
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.dashboard.addon_child_double import PipedChildDouble, answer_with_the_message

TWO_PROJECTS = json.dumps({"entities": [{"type": "PROJECT", "name": "app"}, {"type": "PROJECT", "name": "shop"}]})
APP = json.dumps({"fields": [{"name": "PATH", "atoms": ['"/srv/app"']}]})
SHOP = json.dumps({"fields": [{"name": "PATH", "atoms": ['"/srv/shop"']}]})
FILES_OF_APP = json.dumps({"summary": {"files": 7, "entities": 518}})
NO_FILE = json.dumps({"summary": {"files": 0, "entities": 0}})


class PipedStarterDouble:
    def __init__(self):
        self.requests: list[PipedProcessRequest] = []
        self.children: list[PipedChildDouble] = []

    def start(self, request: PipedProcessRequest) -> PipedChildDouble:
        self.requests.append(request)
        child = PipedChildDouble(answer_with_the_message)
        self.children.append(child)
        return child


class StartAwawaAddonTestCase(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.paths = create_test_paths(Path(root.name))
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")
        self.starter = PipedStarterDouble()

    def create_runtime(self, files_of_app: str):
        runner = ScriptedProcessRunner(
            {
                ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=TWO_PROJECTS),
                ("awawa", "show", "@PROJECT.app"): ProcessAnswer(stdout=APP),
                ("awawa", "show", "@PROJECT.shop"): ProcessAnswer(stdout=SHOP),
                ("awawa", "status", "--json", "/srv/app"): ProcessAnswer(stdout=files_of_app),
                ("awawa", "status", "--json", "/srv/shop"): ProcessAnswer(stdout=NO_FILE),
            }
        )
        return create_test_runtime(self.paths, run_process=runner.run, start_piped_process=self.starter.start)


class StartAwawaAddonForAProjectHoldingACorpusTest(StartAwawaAddonTestCase):
    def test_should_start_one_child_serving_the_projects_holding_a_corpus(self):
        # Arrange
        runtime = self.create_runtime(FILES_OF_APP)

        # Act
        with start_awawa_addon(runtime) as addon:
            holders = addon.holders

        # Assert
        self.assertEqual(holders, frozenset({"app"}))
        self.assertEqual(
            self.starter.requests,
            [
                PipedProcessRequest(
                    argv=(sys.executable, "/srv/brigade/bin/brigade", "awawa-addon"), cwd=str(self.paths.home)
                )
            ],
        )

    def test_should_stop_the_child_once_serving_stops(self):
        # Arrange
        runtime = self.create_runtime(FILES_OF_APP)

        # Act
        with start_awawa_addon(runtime):
            pass

        # Assert
        self.assertFalse(self.starter.children[0].is_running())


class StartAwawaAddonWithoutAProjectHoldingACorpusTest(StartAwawaAddonTestCase):
    def test_should_start_no_child(self):
        # Arrange
        runtime = self.create_runtime(NO_FILE)

        # Act
        with start_awawa_addon(runtime) as addon:
            holders = addon.holders

        # Assert
        self.assertEqual(holders, frozenset())
        self.assertEqual(self.starter.requests, [])


class StartAwawaAddonWithoutARegistryTest(unittest.TestCase):
    def test_should_start_no_child_and_run_no_process(self):
        # Arrange
        runtime = create_test_runtime()

        # Act
        with start_awawa_addon(runtime) as addon:
            holders = addon.holders

        # Assert
        self.assertEqual(holders, frozenset())


class StartAwawaAddonWithoutAwawaTest(StartAwawaAddonTestCase):
    def test_should_start_no_child(self):
        # Arrange
        runner = ScriptedProcessRunner({("awawa",): ToolNotFound("awawa not on PATH")})
        runtime = create_test_runtime(self.paths, run_process=runner.run, start_piped_process=self.starter.start)

        # Act
        with start_awawa_addon(runtime) as addon:
            holders = addon.holders

        # Assert
        self.assertEqual(holders, frozenset())
        self.assertEqual(self.starter.requests, [])
