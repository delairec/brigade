import unittest

from brigade.runs.run_record import RunRecord

RECORD_OF_A_PROJECT_RUN = {
    "schema_version": 1,
    "run": "20261008T090000Z-b74a01",
    "procedure": "deliver",
    "procedure_path": "built-in",
    "slot": "build",
    "role": "builder",
    "role_source": "built-in",
    "client": "claude-code",
    "project": "tidepool",
    "cwd": "/home/user/tidepool",
    "worktree": "/home/user/tidepool",
    "capabilities": ["read", "write"],
    "budget": 40,
    "wall_limit_s": 1500.0,
    "arguments": {"task": "@TASK.B74"},
    "wave": None,
    "task": None,
    "brief": None,
}


class RunRecordTest(unittest.TestCase):
    def test_should_write_back_the_record_of_a_project_run(self):
        # Act
        document = RunRecord.from_document(RECORD_OF_A_PROJECT_RUN).to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "run": "20261008T090000Z-b74a01",
                "procedure": "deliver",
                "procedure_path": "built-in",
                "slot": "build",
                "role": "builder",
                "role_source": "built-in",
                "client": "claude-code",
                "project": "tidepool",
                "cwd": "/home/user/tidepool",
                "worktree": "/home/user/tidepool",
                "capabilities": ["read", "write"],
                "budget": 40,
                "wall_limit_s": 1500.0,
                "arguments": {"task": "@TASK.B74"},
                "wave": None,
                "task": None,
                "brief": None,
            },
        )

    def test_should_write_back_the_record_of_a_run_given_no_project(self):
        # Arrange
        document = {**RECORD_OF_A_PROJECT_RUN, "project": None}

        # Act
        project = RunRecord.from_document(document).to_document()["project"]

        # Assert
        self.assertIsNone(project)
