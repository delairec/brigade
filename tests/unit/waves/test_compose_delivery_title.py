import unittest

from brigade.waves.compose_delivery_title import compose_delivery_title
from brigade.waves.delivery import DeliveredMilestone, DeliveredTask, Delivery

NO_MERGED_WAVE = ()
NO_COMMIT = ()
NO_ATTRIBUTION = ()
NO_REPORT = None
NO_WAVE = None
TIDES = DeliveredMilestone(name="M4", title="Tides")
KEEP_THE_CUT_BRANCH = DeliveredTask(
    name="T7",
    title="The cut branch is kept",
    type="fix",
    component="waves",
    pr=41,
    pr_title="fix(waves): keep the cut branch (@TASK.T7)",
    pr_commits=(),
)
NAME_THE_BASE = DeliveredTask(
    name="T9",
    title="The base is named",
    type="fix",
    component="waves",
    pr=42,
    pr_title="fix(waves): name the base (@TASK.T9)",
    pr_commits=(),
)


def create_delivery(wave: str | None, tasks: tuple[DeliveredTask, ...]) -> Delivery:
    return Delivery(
        wave=wave,
        milestone=TIDES,
        base="integration/tides",
        merged_waves=NO_MERGED_WAVE,
        tasks=tasks,
        commits=NO_COMMIT,
        attribution=NO_ATTRIBUTION,
        report=NO_REPORT,
    )


def create_task(name: str, task_type: str, component: str | None) -> DeliveredTask:
    return DeliveredTask(
        name=name,
        title="A task",
        type=task_type,
        component=component,
        pr=40,
        pr_title=f"{task_type}: do {name} (@TASK.{name})",
        pr_commits=(),
    )


class ComposeDeliveryTitleTest(unittest.TestCase):
    def test_should_title_a_wave_delivering_one_task_as_the_pull_request_of_that_task(self):
        # Arrange
        delivery = create_delivery("tidepool_w16", (KEEP_THE_CUT_BRANCH,))

        # Act
        title = compose_delivery_title(delivery)

        # Assert
        self.assertEqual(title, "fix(waves): keep the cut branch (@TASK.T7)")

    def test_should_add_the_milestone_to_the_title_of_the_one_task_a_milestone_delivers(self):
        # Arrange
        delivery = create_delivery(NO_WAVE, (KEEP_THE_CUT_BRANCH,))

        # Act
        title = compose_delivery_title(delivery)

        # Assert
        self.assertEqual(title, "fix(waves): keep the cut branch (M4, @TASK.T7)")

    def test_should_join_the_subjects_of_several_tasks_in_their_order(self):
        # Arrange
        delivery = create_delivery("tidepool_w16", (KEEP_THE_CUT_BRANCH, NAME_THE_BASE))

        # Act
        title = compose_delivery_title(delivery)

        # Assert
        self.assertEqual(title, "fix(waves): keep the cut branch; name the base (@TASK.T7, @TASK.T9)")

    def test_should_name_the_milestone_before_the_tasks_a_milestone_delivers(self):
        # Arrange
        delivery = create_delivery(NO_WAVE, (KEEP_THE_CUT_BRANCH, NAME_THE_BASE))

        # Act
        title = compose_delivery_title(delivery)

        # Assert
        self.assertEqual(title, "fix(waves): keep the cut branch; name the base (M4, @TASK.T7, @TASK.T9)")

    def test_should_type_the_delivery_feat_over_fix_over_the_type_of_the_first_task(self):
        rows = (
            ("fix", "feat", "feat(waves): do T1; do T2 (@TASK.T1, @TASK.T2)"),
            ("docs", "fix", "fix(waves): do T1; do T2 (@TASK.T1, @TASK.T2)"),
            ("docs", "test", "docs(waves): do T1; do T2 (@TASK.T1, @TASK.T2)"),
        )
        for first_type, second_type, expected in rows:
            with self.subTest(first_type=first_type, second_type=second_type):
                # Arrange
                delivery = create_delivery(
                    "tidepool_w16", (create_task("T1", first_type, "waves"), create_task("T2", second_type, "waves"))
                )

                # Act
                title = compose_delivery_title(delivery)

                # Assert
                self.assertEqual(title, expected)

    def test_should_scope_the_delivery_by_the_component_every_task_shares_its_spaces_hyphenated(self):
        # Arrange
        delivery = create_delivery(
            "tidepool_w16", (create_task("T1", "fix", "the tick"), create_task("T2", "fix", "the tick"))
        )

        # Act
        title = compose_delivery_title(delivery)

        # Assert
        self.assertEqual(title, "fix(the-tick): do T1; do T2 (@TASK.T1, @TASK.T2)")

    def test_should_leave_the_scope_out_when_no_task_names_a_component(self):
        # Arrange
        delivery = create_delivery("tidepool_w16", (create_task("T1", "fix", None), create_task("T2", "fix", None)))

        # Act
        title = compose_delivery_title(delivery)

        # Assert
        self.assertEqual(title, "fix: do T1; do T2 (@TASK.T1, @TASK.T2)")

    def test_should_leave_the_scope_out_when_the_components_differ(self):
        # Arrange
        delivery = create_delivery(
            "tidepool_w16", (create_task("T1", "fix", "the tick"), create_task("T2", "fix", "waves"))
        )

        # Act
        title = compose_delivery_title(delivery)

        # Assert
        self.assertEqual(title, "fix: do T1; do T2 (@TASK.T1, @TASK.T2)")


if __name__ == "__main__":
    unittest.main()
