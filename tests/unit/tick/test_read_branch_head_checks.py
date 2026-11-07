import unittest

from brigade.corpus.read_entities import Entity, EntityField
from brigade.tick.head_proof import ForgeCheck
from brigade.tick.read_branch_head_checks import BranchHeadQuery, read_branch_head_checks
from tests.unit.create_test_runtime import create_test_runtime

GITHUB_PROJECT = Entity(
    name="oak",
    fields=(EntityField(name="PATH", value="/srv/oak"), EntityField(name="FORGE", value="github")),
)
PROJECT_WITHOUT_FORGE = Entity(
    name="oak",
    fields=(EntityField(name="PATH", value="/srv/oak"), EntityField(name="FORGE", value="none")),
)


def read_the_cli_environment(key: str) -> dict:
    return {"GH_TOKEN": f"token-of-{key}"}


class CheckRunsForgeDouble:
    def __init__(self, check_runs: list[dict]):
        self.check_runs = check_runs
        self.requests = []

    def list_check_runs(self, request: dict, runtime) -> dict:
        self.requests.append(request)
        return {"schema_version": 1, "check_runs": self.check_runs}


def create_check_run(head: str, name: str, conclusion: str) -> dict:
    return {
        "pull_request": None,
        "branch": "integration/w1",
        "head": head,
        "name": name,
        "conclusion": conclusion,
        "link": f"https://github.com/delairec/oak/actions/runs/1/job/{name}",
    }


def resolve(forge: CheckRunsForgeDouble):
    def resolve_plugin(kind: str, name: str):
        if (kind, name) != ("forge", "github"):
            raise AssertionError(f"the {kind} plugin {name} should not be resolved")
        return forge

    return resolve_plugin


class ReadBranchHeadChecksTest(unittest.TestCase):
    def test_should_read_the_check_runs_of_the_forge_on_the_commit_of_the_branch_head(self):
        # Arrange
        forge = CheckRunsForgeDouble(
            [create_check_run("c0ffee", "unit", "success"), create_check_run("0ld4ead", "unit", "failure")]
        )
        runtime = create_test_runtime(resolve_plugin=resolve(forge))
        query = BranchHeadQuery(
            project=GITHUB_PROJECT, branch="integration/w1", commit="c0ffee", read_environment=read_the_cli_environment
        )

        # Act
        checks = read_branch_head_checks(runtime, query)

        # Assert
        self.assertEqual(checks, (ForgeCheck(name="unit", verdict="success"),))

    def test_should_ask_the_check_runs_of_the_branch_as_the_cli_account(self):
        # Arrange
        forge = CheckRunsForgeDouble([])
        runtime = create_test_runtime(resolve_plugin=resolve(forge))
        query = BranchHeadQuery(
            project=GITHUB_PROJECT, branch="integration/w1", commit="c0ffee", read_environment=read_the_cli_environment
        )

        # Act
        read_branch_head_checks(runtime, query)

        # Assert
        self.assertEqual(
            forge.requests,
            [
                {
                    "schema_version": 1,
                    "repository": "/srv/oak",
                    "branch": "integration/w1",
                    "environment": {"GH_TOKEN": "token-of-cli"},
                }
            ],
        )

    def test_should_read_no_check_run_for_a_project_off_github(self):
        # Arrange
        runtime = create_test_runtime()
        query = BranchHeadQuery(
            project=PROJECT_WITHOUT_FORGE,
            branch="integration/w1",
            commit="c0ffee",
            read_environment=read_the_cli_environment,
        )
        no_forge_check = ()

        # Act
        checks = read_branch_head_checks(runtime, query)

        # Assert
        self.assertEqual(checks, no_forge_check)
