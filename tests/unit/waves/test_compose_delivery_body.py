import unittest

from brigade.waves.compose_delivery_body import compose_delivery_body
from brigade.waves.delivery import DeliveredMilestone, DeliveredTask, DeliveredWave, Delivery

NO_MERGED_WAVE = ()
NO_COMMIT = ()
NO_ATTRIBUTION = ()
NO_REPORT = None
NO_WAVE = None
NO_MILESTONE = None
TIDES = DeliveredMilestone(name="M4", title="Tides")
KEEP_THE_CUT_BRANCH = DeliveredTask(
    name="T7",
    title="The cut branch is kept",
    type="fix",
    component="waves",
    pr=41,
    pr_title="fix(waves): keep the cut branch (@TASK.T7)",
    pr_commits=("test(waves): keep the cut branch (@TASK.T7)", "fix(waves): keep the cut branch (@TASK.T7)"),
)
NAME_THE_BASE = DeliveredTask(
    name="T9",
    title="The base is named",
    type="fix",
    component="waves",
    pr=42,
    pr_title="fix(waves): name the base (@TASK.T9)",
    pr_commits=("fix(waves): name the base (@TASK.T9)",),
)


class ComposeDeliveryBodyOfAWaveTest(unittest.TestCase):
    def test_should_name_the_wave_its_tasks_and_the_other_commits_of_its_head_then_the_attribution(self):
        # Arrange
        delivery = Delivery(
            wave="tidepool_w16",
            milestone=TIDES,
            base="integration/tides",
            merged_waves=NO_MERGED_WAVE,
            tasks=(KEEP_THE_CUT_BRANCH, NAME_THE_BASE),
            commits=(
                "test(waves): keep the cut branch (@TASK.T7)",
                "chore(tick): pin the timer",
                "fix(waves): name the base (@TASK.T9)",
                "docs(tick): name the timer",
            ),
            attribution=("Co-Authored-By: Octo <octo@example.com>",),
            report=NO_REPORT,
        )

        # Act
        body = compose_delivery_body(delivery)

        # Assert
        self.assertEqual(
            body.splitlines(),
            [
                "Delivers the wave tidepool_w16 of the milestone M4 (Tides) into integration/tides: @TASK.T7, @TASK.T9.",
                "",
                "- @TASK.T7 — The cut branch is kept (#41)",
                "- @TASK.T9 — The base is named (#42)",
                "- chore(tick): pin the timer",
                "- docs(tick): name the timer",
                "",
                "Co-Authored-By: Octo <octo@example.com>",
            ],
        )

    def test_should_name_a_wave_of_tasks_naming_no_milestone_a_wave_of_no_milestone(self):
        # Arrange
        delivery = Delivery(
            wave="tidepool_w16",
            milestone=NO_MILESTONE,
            base="main",
            merged_waves=NO_MERGED_WAVE,
            tasks=(KEEP_THE_CUT_BRANCH,),
            commits=NO_COMMIT,
            attribution=NO_ATTRIBUTION,
            report=NO_REPORT,
        )

        # Act
        body = compose_delivery_body(delivery)

        # Assert
        self.assertEqual(
            body,
            "Delivers the wave tidepool_w16 of no milestone into main: @TASK.T7.\n\n- @TASK.T7 — The cut branch is kept (#41)",
        )

    def test_should_leave_out_the_implemented_marks_and_the_report_brigade_committed(self):
        # Arrange
        delivery = Delivery(
            wave="tidepool_w16",
            milestone=TIDES,
            base="integration/tides",
            merged_waves=NO_MERGED_WAVE,
            tasks=(KEEP_THE_CUT_BRANCH,),
            commits=(
                "docs(corpus): mark @TASK.T7 implemented, delivered by #41",
                "docs(waves): add the report of tidepool_w16",
            ),
            attribution=NO_ATTRIBUTION,
            report=NO_REPORT,
        )

        # Act
        body = compose_delivery_body(delivery)

        # Assert
        self.assertEqual(
            body.splitlines(),
            [
                "Delivers the wave tidepool_w16 of the milestone M4 (Tides) into integration/tides: @TASK.T7.",
                "",
                "- @TASK.T7 — The cut branch is kept (#41)",
            ],
        )

    def test_should_be_the_report_alone_once_the_head_holds_the_report_of_the_wave(self):
        # Arrange
        delivery = Delivery(
            wave="tidepool_w16",
            milestone=TIDES,
            base="integration/tides",
            merged_waves=NO_MERGED_WAVE,
            tasks=(KEEP_THE_CUT_BRANCH,),
            commits=("chore(tick): pin the timer",),
            attribution=("Co-Authored-By: Octo <octo@example.com>",),
            report="# Wave tidepool_w16\n\nT7 merged #41\n",
        )

        # Act
        body = compose_delivery_body(delivery)

        # Assert
        self.assertEqual(body, "# Wave tidepool_w16\n\nT7 merged #41\n")


class ComposeDeliveryBodyOfAMilestoneTest(unittest.TestCase):
    def test_should_name_the_milestone_and_its_merged_waves_with_their_pull_requests(self):
        # Arrange
        delivery = Delivery(
            wave=NO_WAVE,
            milestone=TIDES,
            base="main",
            merged_waves=(DeliveredWave(wave="tidepool_w16", pr=57), DeliveredWave(wave="tidepool_w17", pr=63)),
            tasks=(NAME_THE_BASE,),
            commits=("fix(waves): name the base (@TASK.T9)",),
            attribution=NO_ATTRIBUTION,
            report=NO_REPORT,
        )

        # Act
        body = compose_delivery_body(delivery)

        # Assert
        self.assertEqual(
            body.splitlines(),
            [
                "Delivers the milestone M4 (Tides) into main: its waves tidepool_w16 (#57), tidepool_w17 (#63).",
                "",
                "- @TASK.T9 — The base is named (#42)",
            ],
        )


if __name__ == "__main__":
    unittest.main()
