from brigade.errors import BrigadeError
from brigade.processes.show_invocation import show_invocation
from tests.unit.processes.state_with_trails import StateWithTrailsTestCase


class ShowInvocationTest(StateWithTrailsTestCase):
    def test_should_show_every_process_of_the_invocation(self):
        # Act
        document = show_invocation(self.state_root, "20261010T090000Z-b86a01", failed_only=False)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "kind": "run",
                "id": "20261010T090000Z-b86a01",
                "processes": [{"outcome": "exited", "exit": 0}, {"outcome": "exited", "exit": 1}],
            },
        )

    def test_should_keep_only_the_failed_processes_when_asked(self):
        # Act
        document = show_invocation(self.state_root, "20261010T090000Z-b86a01", failed_only=True)

        # Assert
        self.assertEqual(document["processes"], [{"outcome": "exited", "exit": 1}])

    def test_should_show_a_tick_and_a_command_by_the_id_their_trail_bears(self):
        for invocation_id, expected in [
            (
                "20261010T100000Z",
                {
                    "schema_version": 1,
                    "kind": "tick",
                    "id": "20261010T100000Z",
                    "processes": [{"outcome": "timed_out", "exit": None}],
                },
            ),
            (
                "20261010T080000Z-ab12",
                {
                    "schema_version": 1,
                    "kind": "command",
                    "id": "20261010T080000Z-ab12",
                    "processes": [{"outcome": "exited", "exit": 0}],
                },
            ),
        ]:
            with self.subTest(invocation_id=invocation_id):
                # Act
                document = show_invocation(self.state_root, invocation_id, failed_only=False)

                # Assert
                self.assertEqual(document, expected)

    def test_should_refuse_an_invocation_with_no_trail(self):
        for invocation_id, message in [
            ("20261012T000000Z", "no run, tick or command 20261012T000000Z"),
            ("../runs/20261010T090000Z-b86a01", "no run, tick or command ../runs/20261010T090000Z-b86a01"),
        ]:
            with self.subTest(invocation_id=invocation_id):
                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    show_invocation(self.state_root, invocation_id, failed_only=False)

                # Assert
                self.assertEqual(str(refusal.exception), message)
