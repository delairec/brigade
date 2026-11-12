import tempfile
import unittest
from pathlib import Path

from brigade.commands._list_branch_check_runs import list_branch_check_runs
from brigade.system.parse_configuration import Configuration
from tests.unit.commands.create_plugin_resolver import create_plugin_resolver
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble

FAILED_TESTS = {
    "pull_request": 12,
    "branch": "feature/B7-tides",
    "head": "0123abc",
    "name": "tests",
    "conclusion": "failure",
    "link": "https://forge.example/tidepool/runs/7",
}


class ListBranchCheckRunsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_should_list_the_check_runs_through_the_forge_it_names(self):
        # Arrange
        forge = ForgeDouble({"list_check_runs": lambda request: {"schema_version": 1, "check_runs": [FAILED_TESTS]}})
        runtime = create_test_runtime(
            create_test_paths(self.root), resolve_plugin=create_plugin_resolver({("forge", "forgejo"): forge})
        )
        list_check_runs = list_branch_check_runs(runtime, Configuration(), "forgejo")

        # Act
        check_runs = list_check_runs("/srv/tidepool", "feature/B7-tides")

        # Assert
        self.assertEqual(check_runs, [FAILED_TESTS])

    def test_should_resolve_no_forge_and_read_no_login_environment_for_a_project_of_forge_none(self):
        # Arrange
        no_forge_plugin = {}
        runtime = create_test_runtime(
            create_test_paths(self.root), resolve_plugin=create_plugin_resolver(no_forge_plugin)
        )

        # Act
        check_runs = list_branch_check_runs(runtime, Configuration(forge_accounts={"cli": "octo"}), "none")(
            "/srv/tidepool", "feature/B7-tides"
        )

        # Assert
        self.assertEqual(check_runs, [])
