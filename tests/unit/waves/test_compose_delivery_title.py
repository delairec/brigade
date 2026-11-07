import unittest

from brigade.waves.compose_delivery_title import DeliveredTask, Delivery, compose_delivery_title


class ComposeDeliveryTitleTest(unittest.TestCase):
    def test_should_title_the_delivery_by_the_subject_and_the_name_of_its_milestone(self):
        # Arrange
        delivery = Delivery(
            milestone="M6",
            subject="harden the tick against moved heads and lost branches",
            tasks=(DeliveredTask(name="B227", type="fix", component="tick"),),
        )

        # Act
        title = compose_delivery_title(delivery)

        # Assert
        self.assertEqual(title, "fix(tick): harden the tick against moved heads and lost branches (M6)")

    def test_should_type_the_delivery_feat_over_fix_over_the_type_of_the_first_task_by_number(self):
        for case, types, expected_type in [
            ("a feat among fixes", ("fix", "feat", "docs"), "feat"),
            ("a fix among others", ("docs", "test", "fix"), "fix"),
            ("neither feat nor fix", ("refactor", "docs", "test"), "docs"),
        ]:
            with self.subTest(case=case):
                # Arrange
                type_of_b10, type_of_b9, type_of_b11 = types
                delivery = Delivery(
                    milestone="M6",
                    subject="harden the tick",
                    tasks=(
                        DeliveredTask(name="B10", type=type_of_b10, component="tick"),
                        DeliveredTask(name="B9", type=type_of_b9, component="tick"),
                        DeliveredTask(name="B11", type=type_of_b11, component="tick"),
                    ),
                )

                # Act
                title = compose_delivery_title(delivery)

                # Assert
                self.assertEqual(title, f"{expected_type}(tick): harden the tick (M6)")

    def test_should_scope_the_delivery_by_the_component_every_task_shares_with_hyphens_for_its_spaces(self):
        # Arrange
        delivery = Delivery(
            milestone="M6",
            subject="harden the tick",
            tasks=(
                DeliveredTask(name="B1", type="fix", component="the tick"),
                DeliveredTask(name="B2", type="fix", component="the tick"),
            ),
        )

        # Act
        title = compose_delivery_title(delivery)

        # Assert
        self.assertEqual(title, "fix(the-tick): harden the tick (M6)")

    def test_should_leave_the_scope_out_when_the_components_of_the_tasks_differ(self):
        for case, components in [
            ("two components", ("tick", "ledger")),
            ("a task without a component", ("tick", None)),
            ("no task with a component", (None, None)),
        ]:
            with self.subTest(case=case):
                # Arrange
                component_of_b1, component_of_b2 = components
                delivery = Delivery(
                    milestone="M6",
                    subject="harden the tick",
                    tasks=(
                        DeliveredTask(name="B1", type="fix", component=component_of_b1),
                        DeliveredTask(name="B2", type="fix", component=component_of_b2),
                    ),
                )

                # Act
                title = compose_delivery_title(delivery)

                # Assert
                self.assertEqual(title, "fix: harden the tick (M6)")

    def test_should_title_a_head_delivering_no_task_as_the_report_of_its_milestone_alone(self):
        # Arrange
        no_task_implemented = ()
        delivery = Delivery(milestone="M6", subject="harden the tick", tasks=no_task_implemented)

        # Act
        title = compose_delivery_title(delivery)

        # Assert
        self.assertEqual(title, "docs(milestone): report a milestone delivering no task (M6)")


if __name__ == "__main__":
    unittest.main()
