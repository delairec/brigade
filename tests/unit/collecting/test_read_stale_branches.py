from brigade.collecting.read_stale_branches import read_stale_branches
from brigade.registry.read_projects import read_projects
from tests.unit.collectors.scan_fixtures import (
    LOCAL_BRANCHES_LISTING,
    ScanCollectorTestCase,
    create_equipment,
    create_forge,
)

PULL_REQUESTS = [
    {"number": 3, "head": "main", "state": "merged"},
    {"number": 4, "head": "task/w1/B1", "state": "merged"},
    {"number": 5, "head": "task/w1/B2", "state": "open"},
    {"number": 6, "head": "feat/x", "state": "closed"},
    {"number": 8, "head": "feat/y", "state": "closed"},
    {"number": 9, "head": "feat/y", "state": "open"},
    {"number": 2, "head": "deleted", "state": "merged"},
]


class ReadStaleBranchesTest(ScanCollectorTestCase):
    def setUp(self):
        super().setUp()
        self.register_oak()
        self.processes.answer(LOCAL_BRANCHES_LISTING, stdout="main\ntask/w1/B1\ntask/w1/B2\nspike\nfeat/x\nfeat/y\n")

    def test_should_read_the_local_branches_whose_pull_requests_are_all_merged_or_closed(self):
        # Arrange
        oak = read_projects(self.runtime)[0]

        # Act
        stale = read_stale_branches(oak, create_equipment(create_forge(PULL_REQUESTS)), self.runtime)

        # Assert
        self.assertEqual(
            stale,
            [
                {"branch": "task/w1/B1", "pull_requests": [{"number": 4, "state": "merged"}]},
                {"branch": "feat/x", "pull_requests": [{"number": 6, "state": "closed"}]},
            ],
        )

    def test_should_ask_the_forge_for_the_pull_requests_of_every_state(self):
        # Arrange
        oak = read_projects(self.runtime)[0]
        forge = create_forge([])

        # Act
        read_stale_branches(oak, create_equipment(forge), self.runtime)

        # Assert
        self.assertEqual(
            forge.list_requests("list_pull_requests"),
            [{"schema_version": 1, "repository": "/srv/oak", "state": "all", "environment": {}}],
        )
