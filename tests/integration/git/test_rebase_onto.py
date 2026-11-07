from pathlib import Path

from brigade.git.rebase_onto import rebase_onto
from tests.integration.repository_test_case import IDENTITY, RepositoryTestCase
from tests.integration.run_process_without_trail import run_process_without_trail
from tests.process_launcher import ProcessLauncher

MILESTONE_BRANCH = "integration/hardening"
WAVE_BRANCH = "integration/brigade_w27"


def run_git(repository: Path, *arguments: str) -> str:
    completed = ProcessLauncher.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def commit_tides(repository: Path, tides: str, message: str) -> None:
    (repository / "tides.txt").write_text(tides, encoding="utf-8")
    run_git(repository, "add", "tides.txt")
    run_git(repository, *IDENTITY, "commit", "--quiet", "-m", message)


class RebaseOntoARewrittenBaseTest(RepositoryTestCase):
    def setUp(self):
        super().setUp()
        run_git(self.repository, "config", "user.name", "Ada Lovelace")
        run_git(self.repository, "config", "user.email", "ada@example.org")
        commit_tides(self.repository, "low water\n", "feat: read the tides")
        run_git(self.repository, "checkout", "--quiet", "-b", MILESTONE_BRANCH)
        commit_tides(self.repository, "high water\n", "feat(tick): run each task on its own branch")
        run_git(self.repository, "checkout", "--quiet", "-b", WAVE_BRANCH)

    def rewrite_the_milestone_branch(self) -> None:
        run_git(self.repository, "checkout", "--quiet", "-B", MILESTONE_BRANCH, "main")
        commit_tides(self.repository, "high tide\n", "feat(tick): run each task on its own branch")
        run_git(self.repository, "checkout", "--quiet", WAVE_BRANCH)

    def test_should_bring_a_branch_holding_no_commit_of_its_own_to_the_head_of_its_rewritten_base(self):
        # Arrange
        self.rewrite_the_milestone_branch()

        # Act
        rebase_onto(run_process_without_trail, self.repository, MILESTONE_BRANCH)

        # Assert
        self.assertEqual(
            run_git(self.repository, "rev-parse", "HEAD"), run_git(self.repository, "rev-parse", MILESTONE_BRANCH)
        )

    def test_should_replay_only_the_commits_of_the_branch_onto_its_rewritten_base(self):
        # Arrange
        (self.repository / "README.md").write_text("Wave 27\n", encoding="utf-8")
        run_git(self.repository, "add", "README.md")
        run_git(self.repository, "commit", "--quiet", "-m", "docs: name the wave")
        self.rewrite_the_milestone_branch()

        # Act
        rebase_onto(run_process_without_trail, self.repository, MILESTONE_BRANCH)

        # Assert
        self.assertEqual(
            run_git(self.repository, "log", "--format=%s", "integration/hardening..HEAD"),
            "docs: name the wave\n",
        )
