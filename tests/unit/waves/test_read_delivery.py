import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.waves.delivery import DeliveredMilestone, DeliveredTask, Delivery
from brigade.waves.merged_wave import MergedWave
from brigade.waves.read_delivery import DeliveryDemand, read_delivery

HEAD = "8885daa"
BASE_REF = "origin/integration/tides"
NO_REPORT = None
NO_MERGED_WAVE = ()
ATTRIBUTION = ("Co-Authored-By: Tidepool CLI <cli@tidepool.test>",)
TASK_T9 = (
    ("TITLE", "The base is named"),
    ("TYPE", "fix"),
    ("COMPONENT", "the waves"),
    ("DELIVERED_BY", "42"),
)
TASK_T10 = (("TITLE", "The cut branch is kept"), ("TYPE", "feat"), ("DELIVERED_BY", "43"))
MILESTONE_M4 = (("TITLE", "Tides"),)
PULL_REQUESTS = {
    42: {"title": "fix(the-waves): name the base (@TASK.T9)", "commits": ["fix(waves): name the base"]},
    43: {"title": "feat: keep the cut branch (@TASK.T10)", "commits": ["feat: keep the cut branch"]},
}
LOG = "fix(waves): name the base\nfeat: keep the cut branch\nchore: bump the lock\n"


class CorpusTreesDouble:
    def __init__(self, implemented_by_root: dict, entities: dict):
        self.implemented_by_root = implemented_by_root
        self.entities = entities

    def run(self, request: ProcessRequest) -> ProcessRecord:
        if request.argv[:2] == ("git", "log"):
            return self._answer(request, LOG if request.argv[4] == f"{BASE_REF}..{HEAD}" else "")
        if request.argv[:2] == ("awawa", "status"):
            names = self.implemented_by_root[request.argv[-1]]
            return self._answer(request, json.dumps({"entities": [{"type": "TASK", "name": name} for name in names]}))
        fields = self.entities[request.argv[2]]
        shown = [{"name": name, "atoms": [json.dumps(value)]} for name, value in fields]
        return self._answer(request, json.dumps({"fields": shown}))

    def _answer(self, request: ProcessRequest, stdout: str) -> ProcessRecord:
        return ProcessRecord(argv=request.argv, cwd=request.cwd, exit_code=0, stdout=stdout, stderr="", duration_ms=0)


class ReadDeliveryTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.trees = {HEAD: self.root / "head", BASE_REF: self.root / "base"}
        self.trees[HEAD].mkdir()
        self.trees[BASE_REF].mkdir()
        self.corpus = CorpusTreesDouble(
            {str(self.trees[HEAD]): ["T10", "T5", "T9"], str(self.trees[BASE_REF]): ["T5"]},
            {"@TASK.T9": TASK_T9, "@TASK.T10": TASK_T10, "@MILESTONE.M4": MILESTONE_M4},
        )

    def _demand(self, wave: str | None, report: str | None, merged_waves: tuple = NO_MERGED_WAVE) -> DeliveryDemand:
        return DeliveryDemand(
            wave=wave,
            milestone="M4",
            base="integration/tides",
            base_ref=BASE_REF,
            head=HEAD,
            report=report,
            merged_waves=merged_waves,
            attribution=ATTRIBUTION,
            repository=Path("/srv/tidepool"),
            read_tree=self.trees.__getitem__,
            read_pull_request=PULL_REQUESTS.__getitem__,
        )

    def test_should_gather_the_tasks_the_head_delivers_in_the_order_of_their_numbers_and_its_commits(self):
        # Act
        delivery = read_delivery(self.corpus.run, self._demand("tidepool_w16", "spec/waves/16-report.md"))

        # Assert
        self.assertEqual(
            delivery,
            Delivery(
                wave="tidepool_w16",
                milestone=DeliveredMilestone(name="M4", title="Tides"),
                base="integration/tides",
                merged_waves=(),
                tasks=(
                    DeliveredTask(
                        name="T9",
                        title="The base is named",
                        type="fix",
                        component="the waves",
                        pr=42,
                        pr_title="fix(the-waves): name the base (@TASK.T9)",
                        pr_commits=("fix(waves): name the base",),
                    ),
                    DeliveredTask(
                        name="T10",
                        title="The cut branch is kept",
                        type="feat",
                        component=None,
                        pr=43,
                        pr_title="feat: keep the cut branch (@TASK.T10)",
                        pr_commits=("feat: keep the cut branch",),
                    ),
                ),
                commits=("fix(waves): name the base", "feat: keep the cut branch", "chore: bump the lock"),
                attribution=("Co-Authored-By: Tidepool CLI <cli@tidepool.test>",),
                report=None,
            ),
        )

    def test_should_carry_the_report_the_head_holds(self):
        # Arrange
        (self.trees[HEAD] / "spec" / "waves").mkdir(parents=True)
        (self.trees[HEAD] / "spec" / "waves" / "16-report.md").write_text("# Wave 16\n", encoding="utf-8")

        # Act
        delivery = read_delivery(self.corpus.run, self._demand("tidepool_w16", "spec/waves/16-report.md"))

        # Assert
        self.assertEqual(delivery.report, "# Wave 16\n")

    def test_should_carry_the_merged_waves_of_a_milestone_and_no_report(self):
        # Arrange
        merged_waves = (MergedWave(wave="tidepool_w16", pr=57),)
        no_wave = None

        # Act
        delivery = read_delivery(self.corpus.run, self._demand(no_wave, NO_REPORT, merged_waves))

        # Assert
        self.assertEqual(delivery.merged_waves, (MergedWave(wave="tidepool_w16", pr=57),))
        self.assertIsNone(delivery.report)

    def test_should_carry_no_milestone_for_a_wave_of_tasks_naming_none(self):
        # Arrange
        demand = dataclasses.replace(self._demand("tidepool_w16", "spec/waves/16-report.md"), milestone=None)

        # Act
        delivery = read_delivery(self.corpus.run, demand)

        # Assert
        self.assertIsNone(delivery.milestone)
