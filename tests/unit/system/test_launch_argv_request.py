import unittest

from brigade.system.launch_argv_request import LaunchArgvRequest

LAUNCH_DOCUMENT = {
    "schema_version": 1,
    "worktree": "/home/user/tidepool",
    "brief": "Deliver the task.",
    "role": {
        "name": "builder",
        "package": "You build.",
        "package_file": "/state/runs/20261008T090000Z-b74a01/role.md",
        "capabilities": ["read", "write"],
        "reasoning": "standard",
        "budget": 40,
    },
    "progress_file": "/state/runs/20261008T090000Z-b74a01/progress.md",
}


class LaunchArgvRequestTest(unittest.TestCase):
    def test_should_write_back_the_document_it_read(self):
        # Act
        document = LaunchArgvRequest.from_document(LAUNCH_DOCUMENT).to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "worktree": "/home/user/tidepool",
                "brief": "Deliver the task.",
                "role": {
                    "name": "builder",
                    "package": "You build.",
                    "package_file": "/state/runs/20261008T090000Z-b74a01/role.md",
                    "capabilities": ["read", "write"],
                    "reasoning": "standard",
                    "budget": 40,
                },
                "progress_file": "/state/runs/20261008T090000Z-b74a01/progress.md",
            },
        )
