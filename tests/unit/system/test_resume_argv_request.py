import unittest

from brigade.system.resume_argv_request import ResumeArgvRequest

RESUME_DOCUMENT = {
    "schema_version": 1,
    "worktree": "/home/user/tidepool",
    "brief": "Resume the task.",
    "role": {
        "name": "builder",
        "package": "You build.",
        "package_file": "/state/runs/20261008T090000Z-b74a01/role.md",
        "capabilities": ["read"],
        "reasoning": "deep",
        "budget": 75,
    },
    "progress_file": "/state/runs/20261008T090000Z-b74a01/progress.md",
    "session_id": "session-b74",
    "stop_at": None,
}


class ResumeArgvRequestTest(unittest.TestCase):
    def test_should_write_back_the_document_it_read(self):
        # Act
        document = ResumeArgvRequest.from_document(RESUME_DOCUMENT).to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "worktree": "/home/user/tidepool",
                "brief": "Resume the task.",
                "role": {
                    "name": "builder",
                    "package": "You build.",
                    "package_file": "/state/runs/20261008T090000Z-b74a01/role.md",
                    "capabilities": ["read"],
                    "reasoning": "deep",
                    "budget": 75,
                },
                "progress_file": "/state/runs/20261008T090000Z-b74a01/progress.md",
                "session_id": "session-b74",
                "stop_at": None,
            },
        )
