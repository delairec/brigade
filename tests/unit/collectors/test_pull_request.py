import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.pull_request import collect
from brigade.system.parse_configuration import Configuration
from tests.unit.create_recipe_answers import create_recipe_answers
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

NO_CLIENT_RESOLVER = None
HEAD = "2222222"
WAVE_HEAD = "1111111"
BASE = "0000000"


class ForgeDescribingThePullRequestDouble:
    def read_pull_request(self, request: dict, runtime) -> dict:
        return {
            "schema_version": 1,
            "pull_request": {
                "number": 160,
                "title": "feat(cart): empty the cart",
                "body": "Delivers @TASK.B1.\n",
                "head": "task/w1/B1",
                "head_sha": HEAD,
                "checks": [],
            },
        }


class PullRequestCollectorTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.paths = create_test_paths(self.root)
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")
        self.head_tree = self.paths.cache_root / "refs" / "shop" / HEAD
        self.head_tree.mkdir(parents=True)
        (self.paths.cache_root / "refs" / "shop" / BASE).mkdir(parents=True)

    def test_should_hand_the_argv_of_each_step_of_the_acceptance_recipe_read_in_the_checkout_of_the_head(self):
        # Arrange
        runner = RecordingProcessRunner(
            {
                **create_registry_answers(self.paths.config_root, {"shop": {"PATH": "/srv/shop", "FORGE": "none"}}),
                **create_recipe_answers(self.head_tree, {"acceptance": (("python3", "-m", "unittest"),)}),
                (
                    "git",
                    "rev-parse",
                    "--verify",
                    "--quiet",
                    "--end-of-options",
                    "refs/remotes/origin/integration/w1^{commit}",
                ): ProcessAnswer(stdout=f"{WAVE_HEAD}\n"),
                ("git", "merge-base", "--end-of-options", WAVE_HEAD, HEAD): ProcessAnswer(stdout=f"{BASE}\n"),
                ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{HEAD}^{{commit}}"): ProcessAnswer(
                    stdout=f"{HEAD}\n"
                ),
                ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{BASE}^{{commit}}"): ProcessAnswer(
                    stdout=f"{BASE}\n"
                ),
            }
        )
        environment = {
            "BRIGADE_PROJECT_PATH": "/srv/shop",
            "BRIGADE_SINCE": "2026-10-01",
            "BRIGADE_PARAMS": json.dumps({"pr": "160", "base": "integration/w1", "task": "B1"}),
        }
        equipment = CollectorEquipment(
            configuration=Configuration(),
            forge=ForgeDescribingThePullRequestDouble(),
            forge_name="none",
            resolve_client=NO_CLIENT_RESOLVER,
        )

        # Act
        document = collect(environment, create_test_runtime(self.paths, run_process=runner), equipment)

        # Assert
        self.assertEqual(document["summary"]["acceptance"], [["python3", "-m", "unittest"]])
