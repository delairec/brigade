import unittest
from pathlib import Path

from brigade.system.run_process import ProcessRecord
from brigade.verify.read_repair_diff import RepairSpan, read_repair_diff
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

SPAN = RepairSpan(
    repository=Path("/srv/shop"), wave_head="c0ffee1", judged_head="efd5ed1", head="51dee9a", base="ba5e002"
)
REPAIR = "--- a/src/tides.py\n+++ b/src/tides.py\n@@ -12 +12 @@\n-read()\n+cached()\n"
RANGE_DIFF = "1:  efd5ed1 ! 1:  51dee9a feat(tides): read the tides\n"


class ReadRepairDiffTest(unittest.TestCase):
    def test_should_diff_from_the_judged_head_when_the_current_head_descends_from_it(self):
        # Arrange
        runner = RecordingProcessRunner({("git", "diff", "efd5ed1", "51dee9a"): ProcessAnswer(stdout=REPAIR)})

        # Act
        record = read_repair_diff(runner, SPAN)

        # Assert
        self.assertEqual(
            record,
            ProcessRecord(
                argv=("git", "diff", "efd5ed1", "51dee9a"),
                cwd="/srv/shop",
                exit_code=0,
                stdout=REPAIR,
                stderr="",
                duration_ms=0,
            ),
        )

    def test_should_range_diff_the_commits_on_their_base_at_each_head_after_a_rebase(self):
        # Arrange
        runner = RecordingProcessRunner(
            {
                ("git", "merge-base", "--is-ancestor", "efd5ed1", "51dee9a"): ProcessAnswer(exit_code=1),
                ("git", "merge-base", "--end-of-options", "c0ffee1", "efd5ed1"): ProcessAnswer(stdout="01d0ba5\n"),
                ("git", "range-diff", "01d0ba5..efd5ed1", "ba5e002..51dee9a"): ProcessAnswer(stdout=RANGE_DIFF),
            }
        )

        # Act
        record = read_repair_diff(runner, SPAN)

        # Assert
        self.assertEqual(
            record,
            ProcessRecord(
                argv=("git", "range-diff", "01d0ba5..efd5ed1", "ba5e002..51dee9a"),
                cwd="/srv/shop",
                exit_code=0,
                stdout=RANGE_DIFF,
                stderr="",
                duration_ms=0,
            ),
        )
