import unittest

from brigade.waves.compose_delivery_title import DeliveredTask, Delivery, compose_delivery_title


class ComposeDeliveryTitleTest(unittest.TestCase):
    def test_should_title_a_head_delivering_one_task_by_the_title_of_its_pull_request_with_the_milestone(self):
        # Arrange
        delivery = Delivery(
            milestone="M9",
            tasks=(
                DeliveredTask(
                    name="B223",
                    type="feat",
                    component="tick",
                    pull_request_title="feat(tick): record milestone.rebased when a milestone branch is rebased"
                    " (@TASK.B223)",
                ),
            ),
        )

        # Act
        title = compose_delivery_title(delivery)

        # Assert
        self.assertEqual(
            title, "feat(tick): record milestone.rebased when a milestone branch is rebased (M9, @TASK.B223)"
        )

    def test_should_join_the_subjects_of_several_tasks_in_the_order_of_their_numbers(self):
        # Arrange
        delivery = Delivery(
            milestone="M6",
            tasks=(
                DeliveredTask(
                    name="B10",
                    type="fix",
                    component="tick",
                    pull_request_title="fix(tick): park a dead run (@TASK.B10)",
                ),
                DeliveredTask(
                    name="B9", type="fix", component="tick", pull_request_title="fix(tick): name the base (@TASK.B9)"
                ),
            ),
        )

        # Act
        title = compose_delivery_title(delivery)

        # Assert
        self.assertEqual(title, "fix(tick): name the base; park a dead run (M6, @TASK.B9, @TASK.B10)")

    def test_should_type_the_delivery_feat_over_fix_over_the_type_of_the_first_task(self):
        for case, types, expected_type in [
            ("a feat among fixes", ("fix", "feat", "docs"), "feat"),
            ("a fix among others", ("docs", "test", "fix"), "fix"),
            ("neither feat nor fix", ("docs", "test", "refactor"), "docs"),
        ]:
            with self.subTest(case=case):
                # Arrange
                first, second, third = types
                delivery = Delivery(
                    milestone="M6",
                    tasks=(
                        DeliveredTask(name="B1", type=first, component="tick", pull_request_title=f"{first}(tick): a"),
                        DeliveredTask(
                            name="B2", type=second, component="tick", pull_request_title=f"{second}(tick): b"
                        ),
                        DeliveredTask(name="B3", type=third, component="tick", pull_request_title=f"{third}(tick): c"),
                    ),
                )

                # Act
                title = compose_delivery_title(delivery)

                # Assert
                self.assertEqual(title, f"{expected_type}(tick): a; b; c (M6, @TASK.B1, @TASK.B2, @TASK.B3)")

    def test_should_scope_the_delivery_by_the_component_every_task_shares_with_hyphens_for_its_spaces(self):
        # Arrange
        delivery = Delivery(
            milestone="M6",
            tasks=(
                DeliveredTask(
                    name="B1", type="fix", component="the pass", pull_request_title="fix(the-pass): a (@TASK.B1)"
                ),
                DeliveredTask(
                    name="B2", type="fix", component="the pass", pull_request_title="fix(the-pass): b (@TASK.B2)"
                ),
            ),
        )

        # Act
        title = compose_delivery_title(delivery)

        # Assert
        self.assertEqual(title, "fix(the-pass): a; b (M6, @TASK.B1, @TASK.B2)")

    def test_should_leave_the_scope_out_when_the_components_of_the_tasks_differ(self):
        for case, components in [
            ("two components", ("tick", "ledger")),
            ("a task without a component", ("tick", None)),
            ("no task with a component", (None, None)),
        ]:
            with self.subTest(case=case):
                # Arrange
                first, second = components
                delivery = Delivery(
                    milestone="M6",
                    tasks=(
                        DeliveredTask(
                            name="B1", type="fix", component=first, pull_request_title="fix(tick): a (@TASK.B1)"
                        ),
                        DeliveredTask(name="B2", type="fix", component=second, pull_request_title="fix: b (@TASK.B2)"),
                    ),
                )

                # Act
                title = compose_delivery_title(delivery)

                # Assert
                self.assertEqual(title, "fix: a; b (M6, @TASK.B1, @TASK.B2)")

    def test_should_title_a_head_delivering_no_task_as_the_report_of_its_milestone_alone(self):
        # Arrange
        no_task_implemented = ()
        delivery = Delivery(milestone="M6", tasks=no_task_implemented)

        # Act
        title = compose_delivery_title(delivery)

        # Assert
        self.assertEqual(title, "docs(milestone): report a milestone delivering no task (M6)")


if __name__ == "__main__":
    unittest.main()
