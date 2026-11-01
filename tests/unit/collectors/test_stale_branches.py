from brigade.collectors.stale_branches import collect
from tests.unit.collectors.scan_fixtures import (
    ENVIRONMENT_OF_OAK,
    LOCAL_BRANCHES_LISTING,
    ScanCollectorTestCase,
    create_equipment,
    create_forge,
)

MERGED_PULL_REQUEST = {"number": 4, "head": "task/w1/B1", "state": "merged"}


class StaleBranchesCollectorTest(ScanCollectorTestCase):
    def setUp(self):
        super().setUp()
        self.register_oak()
        self.processes.answer(LOCAL_BRANCHES_LISTING, stdout="main\ntask/w1/B1\n")

    def test_should_print_one_item_per_stale_branch_fingerprinted_by_its_name(self):
        # Act
        document = collect(ENVIRONMENT_OF_OAK, self.runtime, create_equipment(create_forge([MERGED_PULL_REQUEST])))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "stale-branches",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": False,
                "summary": {"branches": 1},
                "items": [
                    {
                        "branch": "task/w1/B1",
                        "pull_requests": [{"number": 4, "state": "merged"}],
                        "fingerprint": "task/w1/B1",
                    }
                ],
            },
        )

    def test_should_only_read_the_branches_and_the_pull_requests(self):
        # Arrange
        forge = create_forge([MERGED_PULL_REQUEST])

        # Act
        collect(ENVIRONMENT_OF_OAK, self.runtime, create_equipment(forge))

        # Assert
        self.assertEqual(self.processes.list_argvs()[-1], LOCAL_BRANCHES_LISTING)
        self.assertEqual(forge.list_operations(), ["list_pull_requests"])
