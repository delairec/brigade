from brigade.processes.list_invocations import list_invocations
from tests.unit.processes.state_with_trails import StateWithTrailsTestCase


class ListInvocationsTest(StateWithTrailsTestCase):
    def test_should_list_the_invocations_newest_first_with_their_failed_processes(self):
        # Act
        invocations = list_invocations(self.state_root)

        # Assert
        self.assertEqual(
            invocations,
            [
                {
                    "kind": "tick",
                    "id": "20261010T100000Z",
                    "instant": "2026-10-10T10:00:00Z",
                    "processes": 1,
                    "failed": 1,
                },
                {
                    "kind": "run",
                    "id": "20261010T090000Z-b86a01",
                    "instant": "2026-10-10T09:00:00Z",
                    "processes": 2,
                    "failed": 1,
                },
                {
                    "kind": "command",
                    "id": "20261010T080000Z-ab12",
                    "instant": "2026-10-10T08:00:00Z",
                    "processes": 1,
                    "failed": 0,
                },
            ],
        )
