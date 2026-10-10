import unittest
from pathlib import Path

from brigade.git.read_upstream_lag import UpstreamLag, read_upstream_lag
from brigade.system.run_process import ProcessRecord

CHECKOUT = Path("/srv/brigade")
ON_MAIN_TRACKING_ORIGIN = " 4f2a9c1 \n* 61100fd origin/main\n"
DETACHED = " 4f2a9c1 \n 61100fd origin/main\n"
ON_A_BRANCH_WITHOUT_UPSTREAM = "* 4f2a9c1 \n 61100fd origin/main\n"
ORIGIN_MAIN_COMMIT = "3deeea2\n"


def create_git(branches: str, counts: str):
    answers = {"for-each-ref": branches, "rev-parse": ORIGIN_MAIN_COMMIT, "rev-list": counts}

    def answer_git(request):
        return ProcessRecord(
            argv=request.argv, cwd=request.cwd, exit_code=0, stdout=answers[request.argv[1]], stderr="", duration_ms=0
        )

    return answer_git


class ReadUpstreamLagOfABranchBehindItsUpstreamTest(unittest.TestCase):
    def test_should_count_the_commits_behind_the_upstream(self):
        rows = [
            ("behind", "3\t0\n"),
            ("diverged", "3\t2\n"),
        ]
        for position, counts in rows:
            with self.subTest(position=position):
                # Arrange
                git = create_git(ON_MAIN_TRACKING_ORIGIN, counts)

                # Act
                lag = read_upstream_lag(git, CHECKOUT)

                # Assert
                self.assertEqual(
                    lag, UpstreamLag(commit="61100fd", upstream="origin/main", upstream_commit="3deeea2", behind=3)
                )


class ReadUpstreamLagWithNothingBehindTest(unittest.TestCase):
    def test_should_read_no_lag(self):
        rows = [
            ("up to date", ON_MAIN_TRACKING_ORIGIN, "0\t0\n"),
            ("only ahead", ON_MAIN_TRACKING_ORIGIN, "0\t2\n"),
            ("detached", DETACHED, "0\t0\n"),
            ("on a branch without upstream", ON_A_BRANCH_WITHOUT_UPSTREAM, "0\t0\n"),
        ]
        for position, branches, counts in rows:
            with self.subTest(position=position):
                # Arrange
                git = create_git(branches, counts)

                # Act
                lag = read_upstream_lag(git, CHECKOUT)

                # Assert
                self.assertIsNone(lag)
