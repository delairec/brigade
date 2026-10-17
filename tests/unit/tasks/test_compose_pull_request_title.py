import unittest

from brigade.errors import BrigadeError
from brigade.tasks.compose_pull_request_title import PullRequestTitleParts, compose_pull_request_title


class ComposePullRequestTitleTest(unittest.TestCase):
    def test_should_scope_the_title_with_the_component_its_spaces_replaced_by_hyphens(self):
        # Arrange
        parts = PullRequestTitleParts(
            type="feat", component="agent side", subject="open the pull request of a task", task="B142"
        )

        # Act
        title = compose_pull_request_title(parts)

        # Assert
        self.assertEqual(title, "feat(agent-side): open the pull request of a task (@TASK.B142)")

    def test_should_leave_the_scope_out_when_the_task_has_no_component(self):
        # Arrange
        no_component = None
        parts = PullRequestTitleParts(type="docs", component=no_component, subject="record the plan", task="S3")

        # Act
        title = compose_pull_request_title(parts)

        # Assert
        self.assertEqual(title, "docs: record the plan (@TASK.S3)")

    def test_should_refuse_a_missing_subject_naming_the_cause(self):
        for missing_subject in (None, "", "   "):
            with self.subTest(subject=missing_subject):
                # Arrange
                parts = PullRequestTitleParts(type="feat", component="tick", subject=missing_subject, task="S3")

                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    compose_pull_request_title(parts)

                # Assert
                self.assertEqual(
                    str(refusal.exception),
                    "brigade task pr needs --subject, the subject of the pull request in the imperative",
                )
