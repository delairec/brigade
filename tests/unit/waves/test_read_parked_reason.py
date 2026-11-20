import unittest

from brigade.ledger.task_parked import TaskParked
from brigade.ledger.task_state import TaskState
from brigade.waves.read_parked_reason import read_parked_reason

PARKED_ON_ITS_RUN = TaskParked(wave="shop_w1", task="S3", reason="its run ended blocked", blockers=())
PARKED_ON_ITS_PREFLIGHT = TaskParked(wave="shop_w1", task="S3", reason="its preflight failed", blockers=())
PARKED_IN_ANOTHER_WAVE = TaskParked(wave="shop_w2", task="S3", reason="its preflight failed", blockers=())
QUEUED_AGAIN = TaskState(wave="shop_w1", task="S3", state="queued")


class ReadParkedReasonTest(unittest.TestCase):
    def test_should_read_the_reason_of_the_last_parking_of_a_task_in_its_wave(self):
        for case, events, expected in [
            ("parked twice", (PARKED_ON_ITS_PREFLIGHT, QUEUED_AGAIN, PARKED_ON_ITS_RUN), "its run ended blocked"),
            ("parked in another wave alone", (PARKED_IN_ANOTHER_WAVE, QUEUED_AGAIN), None),
        ]:
            with self.subTest(case=case):
                # Act
                reason = read_parked_reason(events, "shop_w1", "S3")

                # Assert
                self.assertEqual(reason, expected)


if __name__ == "__main__":
    unittest.main()
