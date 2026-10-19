import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.system.read_configuration import Configuration
from brigade.verify.preflight_pull_request import PreflightDemand, preflight_pull_request
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

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
                "checks": [{"name": "unit", "verdict": "success"}],
            },
        }


class PreflightPullRequestTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.paths = create_test_paths(self.root)
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")
        self.head_tree = self.paths.cache_root / "refs" / "shop" / HEAD
        self.base_tree = self.paths.cache_root / "refs" / "shop" / BASE
        (self.head_tree / "brigade").mkdir(parents=True)
        (self.head_tree / "brigade" / "cart.py").write_text("def empty_cart():\n")
        self.base_tree.mkdir(parents=True)

    def create_runner(self) -> RecordingProcessRunner:
        task = {
            "fields": [
                {"name": "STATUS", "atoms": ["implemented"], "fields": []},
                {"name": "DELIVERED_BY", "atoms": ['"160"'], "fields": []},
                {
                    "name": "SPEC",
                    "atoms": ['"empties the cart"'],
                    "fields": [{"name": "IMPL", "atoms": ['"brigade/cart.py::def empty_cart"'], "fields": []}],
                },
            ]
        }
        return RecordingProcessRunner(
            {
                **create_registry_answers(self.paths.config_root, {"shop": {"PATH": "/srv/shop"}}),
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
                ("git", "diff", "--numstat", "--text", "--end-of-options", BASE, HEAD, "--"): ProcessAnswer(
                    stdout="1\t0\tbrigade/cart.py\n"
                ),
                ("awawa", "show", "@TASK.B1", "--json", str(self.head_tree)): ProcessAnswer(stdout=json.dumps(task)),
                ("awawa", "diff", str(self.base_tree), str(self.head_tree), "--json"): ProcessAnswer(
                    stdout=json.dumps({"added": [], "changed": [], "removed": []})
                ),
            }
        )

    def test_should_run_every_deterministic_check_of_the_pull_request(self):
        # Arrange
        demand = PreflightDemand(
            project=Entity(name="shop", fields=(EntityField(name="PATH", value="/srv/shop"),)),
            task="B1",
            wave_branch="integration/w1",
            pr=160,
            forge=ForgeDescribingThePullRequestDouble(),
            environment={"GH_TOKEN": "token-of-octo-builder"},
            configuration=Configuration(),
        )

        # Act
        document = preflight_pull_request(create_test_runtime(self.paths, run_process=self.create_runner()), demand)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "project": "shop",
                "pr": 160,
                "task": "B1",
                "head": HEAD,
                "checks": [
                    {"name": "ancestry", "verdict": "pass", "findings": []},
                    {"name": "checks", "verdict": "pass", "findings": []},
                    {"name": "corpus", "verdict": "pass", "findings": []},
                    {"name": "promotion", "verdict": "pass", "findings": []},
                    {"name": "untouched_files", "verdict": "pass", "findings": []},
                    {"name": "privacy", "verdict": "pass", "findings": []},
                    {"name": "body", "verdict": "pass", "findings": []},
                    {
                        "name": "size",
                        "verdict": "info",
                        "findings": ["1 files", "1 lines", "1 packages: brigade", "0 layers"],
                    },
                ],
            },
        )
