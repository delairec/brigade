import unittest

from brigade.corpus.read_entities import Entity, EntityField
from brigade.tick.head_proof import ForgeCheck
from brigade.tick.read_branch_head_checks import BranchHeadQuery, read_branch_head_checks

GITHUB_PROJECT = Entity(
    name="oak",
    fields=(EntityField(name="PATH", value="/srv/oak"), EntityField(name="FORGE", value="github")),
)
PROJECT_WITHOUT_FORGE = Entity(
    name="oak",
    fields=(EntityField(name="PATH", value="/srv/oak"), EntityField(name="FORGE", value="none")),
)


class CheckRunsListingDouble:
    def __init__(self, check_runs: list[dict]):
        self.check_runs = check_runs
        self.branches = []

    def list_check_runs(self, repository: str, branch: str) -> list[dict]:
        self.branches.append((repository, branch))
        return self.check_runs


def create_check_run(head: str, conclusion: str) -> dict:
    return {
        "pull_request": None,
        "branch": "integration/w1",
        "head": head,
        "name": "unit",
        "conclusion": conclusion,
        "link": "https://github.com/delairec/oak/actions/runs/1/job/2",
    }


class ReadBranchHeadChecksTest(unittest.TestCase):
    def test_should_read_the_check_runs_of_the_forge_on_the_commit_of_the_branch_head(self):
        # Arrange
        listing = CheckRunsListingDouble(
            [create_check_run("c0ffee", "success"), create_check_run("0ld4ead", "failure")]
        )
        query = BranchHeadQuery(
            project=GITHUB_PROJECT, branch="integration/w1", commit="c0ffee", list_check_runs=listing.list_check_runs
        )

        # Act
        checks = read_branch_head_checks(query)

        # Assert
        self.assertEqual(checks, (ForgeCheck(name="unit", verdict="success"),))

    def test_should_ask_the_check_runs_of_the_branch_in_the_repository_of_the_project(self):
        # Arrange
        listing = CheckRunsListingDouble([])
        query = BranchHeadQuery(
            project=GITHUB_PROJECT, branch="integration/w1", commit="c0ffee", list_check_runs=listing.list_check_runs
        )

        # Act
        read_branch_head_checks(query)

        # Assert
        self.assertEqual(listing.branches, [("/srv/oak", "integration/w1")])

    def test_should_read_no_check_run_for_a_project_off_github(self):
        # Arrange
        listing = CheckRunsListingDouble([create_check_run("c0ffee", "success")])
        query = BranchHeadQuery(
            project=PROJECT_WITHOUT_FORGE,
            branch="integration/w1",
            commit="c0ffee",
            list_check_runs=listing.list_check_runs,
        )
        no_forge_check = ()

        # Act
        checks = read_branch_head_checks(query)

        # Assert
        self.assertEqual(checks, no_forge_check)
