import unittest

from brigade.errors import BrigadeError
from brigade.system.actions_request import ActionsRequest
from brigade.system.read_client_request import read_client_request


class ReadClientRequestTest(unittest.TestCase):
    def test_should_read_the_request_of_the_operation(self):
        # Act
        request = read_client_request("actions", '{"schema_version": 1, "output": "Reading the task"}')

        # Assert
        self.assertEqual(request, ActionsRequest(output="Reading the task"))

    def test_should_refuse_a_request_that_is_not_json(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_client_request("actions", "Reading the task")

        # Assert
        self.assertEqual(
            str(refusal.exception), "the request on stdin is not JSON: Expecting value: line 1 column 1 (char 0)"
        )

    def test_should_refuse_a_request_off_the_shape_of_the_operation(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_client_request("actions", '{"schema_version": 1}')

        # Assert
        self.assertEqual(str(refusal.exception), "the request on stdin: lacks the key output")

    def test_should_refuse_a_launch_or_a_resume_request_lacking_what_the_run_needs(self):
        # Arrange
        rows = [
            (
                "launch-argv",
                '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42.", "role": {"name":'
                ' "builder", "package": "AGENT builder", "package_file": "/state/brigade/runs/r1/role.md",'
                ' "capabilities": ["read"], "reasoning": "standard", "budget": 75}}',
                "the request on stdin: lacks the key progress_file",
            ),
            (
                "launch-argv",
                '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42.",'
                ' "progress_file": "/state/brigade/runs/r1/progress.md", "role": {"name": "builder",'
                ' "package": "AGENT builder", "capabilities": ["read"], "reasoning": "standard", "budget": 75}}',
                "the request on stdin: lacks the key role.package_file",
            ),
            (
                "launch-argv",
                '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42.",'
                ' "progress_file": "/state/brigade/runs/r1/progress.md", "role": {"name": "builder",'
                ' "package": "AGENT builder", "package_file": "/state/brigade/runs/r1/role.md",'
                ' "capabilities": ["read"], "reasoning": "standard", "budget": 75}}',
                "the request on stdin: lacks the key session_id",
            ),
            (
                "resume-argv",
                '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Carry on.",'
                ' "progress_file": "/state/brigade/runs/r1/progress.md", "role": {"name": "builder",'
                ' "package": "AGENT builder", "package_file": "/state/brigade/runs/r1/role.md",'
                ' "capabilities": ["read"], "reasoning": "standard", "budget": 75}}',
                "the request on stdin: lacks the key session_id",
            ),
            (
                "launch-argv",
                '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42.", "session_id":'
                ' "s1", "progress_file": "/state/brigade/runs/r1/progress.md", "role": {"name": "builder",'
                ' "package": "AGENT builder", "package_file": "/state/brigade/runs/r1/role.md",'
                ' "capabilities": ["read"], "reasoning": "standard", "budget": 75}}',
                "the request on stdin: lacks the key stop_at",
            ),
            (
                "resume-argv",
                '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Carry on.", "session_id": "s1",'
                ' "progress_file": "/state/brigade/runs/r1/progress.md", "role": {"name": "builder",'
                ' "package": "AGENT builder", "package_file": "/state/brigade/runs/r1/role.md",'
                ' "capabilities": ["read"], "reasoning": "standard", "budget": 75}}',
                "the request on stdin: lacks the key stop_at",
            ),
            (
                "launch-argv",
                '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42.", "session_id":'
                ' "s1", "stop_at": 1791451380, "progress_file": "/state/brigade/runs/r1/progress.md", "role":'
                ' {"name": "builder", "package": "AGENT builder", "package_file": "/state/brigade/runs/r1/role.md",'
                ' "capabilities": ["read"], "reasoning": "standard", "budget": 75}}',
                "the request on stdin: stop_at is an integer, not a string",
            ),
        ]
        for operation, stdin, expected_refusal in rows:
            with self.subTest(expected_refusal=expected_refusal, operation=operation):
                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    read_client_request(operation, stdin)

                # Assert
                self.assertEqual(str(refusal.exception), expected_refusal)
