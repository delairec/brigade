import json
import os

from brigade.collectors.stale_worktrees import collect
from brigade.runs.record_run_pid import record_run_pid
from tests.unit.collectors.scan_fixtures import (
    ENVIRONMENT_OF_OAK,
    LOCAL_BRANCHES_LISTING,
    ScanCollectorTestCase,
    create_equipment,
    create_forge,
)

WORKTREE_LISTING = ("git", "worktree", "list", "--porcelain", "-z")
WORKTREES = (
    "worktree /srv/oak\0HEAD a0\0branch refs/heads/task/w1/B1\0\0"
    "worktree /srv/oak/.brigade/worktrees/B1\0HEAD b1\0branch refs/heads/task/w1/B1\0\0"
    "worktree /srv/oak/.brigade/worktrees/B2\0HEAD b2\0branch refs/heads/task/w1/B2\0\0"
    "worktree /srv/oak/.brigade/worktrees/B3\0HEAD b3\0branch refs/heads/task/w1/B3\0\0"
    "worktree /srv/oak/.brigade/worktrees/B4\0HEAD b4\0detached\0\0"
    "worktree /srv/oak/.brigade/worktrees/B5\0HEAD b5\0detached\0\0"
)
PULL_REQUESTS = [
    {"number": 4, "head": "task/w1/B1", "state": "merged"},
    {"number": 5, "head": "task/w1/B2", "state": "open"},
]


class StaleWorktreesCollectorTest(ScanCollectorTestCase):
    def setUp(self):
        super().setUp()
        self.register_oak()
        self.processes.answer(WORKTREE_LISTING, stdout=WORKTREES)
        self.processes.answer(LOCAL_BRANCHES_LISTING, stdout="main\ntask/w1/B1\ntask/w1/B2\n")
        self.record_run("20261019T080000Z-live", "/srv/oak/.brigade/worktrees/B4")
        self.record_run("20261019T070000Z-dead", "/srv/oak/.brigade/worktrees/B5")
        record_run_pid(self.root / "state" / "runs" / "20261019T080000Z-live", pid=os.getpid())

    def record_run(self, run: str, cwd: str) -> None:
        directory = self.root / "state" / "runs" / run
        directory.mkdir(parents=True)
        (directory / "run.json").write_text(json.dumps({"cwd": cwd}), encoding="utf-8")

    def test_should_print_the_linked_worktrees_of_a_stale_or_missing_branch_or_detached_with_no_live_run(self):
        # Act
        document = collect(ENVIRONMENT_OF_OAK, self.runtime, create_equipment(create_forge(PULL_REQUESTS)))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "stale-worktrees",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": False,
                "summary": {"worktrees": 3},
                "items": [
                    {
                        "path": "/srv/oak/.brigade/worktrees/B1",
                        "branch": "task/w1/B1",
                        "head": "b1",
                        "reason": "stale branch",
                        "fingerprint": "/srv/oak/.brigade/worktrees/B1",
                    },
                    {
                        "path": "/srv/oak/.brigade/worktrees/B3",
                        "branch": "task/w1/B3",
                        "head": "b3",
                        "reason": "missing branch",
                        "fingerprint": "/srv/oak/.brigade/worktrees/B3",
                    },
                    {
                        "path": "/srv/oak/.brigade/worktrees/B5",
                        "branch": None,
                        "head": "b5",
                        "reason": "detached with no live run",
                        "fingerprint": "/srv/oak/.brigade/worktrees/B5",
                    },
                ],
            },
        )

    def test_should_only_read_the_worktrees_the_branches_and_the_pull_requests(self):
        # Arrange
        forge = create_forge(PULL_REQUESTS)

        # Act
        collect(ENVIRONMENT_OF_OAK, self.runtime, create_equipment(forge))

        # Assert
        self.assertEqual(
            self.processes.list_argvs()[-3:], [WORKTREE_LISTING, LOCAL_BRANCHES_LISTING, LOCAL_BRANCHES_LISTING]
        )
        self.assertEqual(forge.list_operations(), ["list_pull_requests"])

    def test_should_print_the_missing_and_detached_worktrees_of_a_project_off_the_forge(self):
        # Arrange
        self.register_oak(("FORGE", "none"))
        forge = create_forge(PULL_REQUESTS)

        # Act
        document = collect(ENVIRONMENT_OF_OAK, self.runtime, create_equipment(forge))

        # Assert
        self.assertEqual(
            document["items"],
            [
                {
                    "path": "/srv/oak/.brigade/worktrees/B3",
                    "branch": "task/w1/B3",
                    "head": "b3",
                    "reason": "missing branch",
                    "fingerprint": "/srv/oak/.brigade/worktrees/B3",
                },
                {
                    "path": "/srv/oak/.brigade/worktrees/B5",
                    "branch": None,
                    "head": "b5",
                    "reason": "detached with no live run",
                    "fingerprint": "/srv/oak/.brigade/worktrees/B5",
                },
            ],
        )
        self.assertEqual(forge.list_operations(), [])
