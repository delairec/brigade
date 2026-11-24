import unittest

from brigade.dashboard.read_signal_origin import SignalOrigin, read_signal_origin


def create_signal(kind: str, fingerprint: str, project: str | None) -> dict:
    return {"kind": kind, "fingerprint": fingerprint, "project": project}


class ReadSignalOriginTest(unittest.TestCase):
    def test_should_group_a_signal_under_what_recorded_it_and_name_its_subject(self):
        # Arrange
        rows = [
            (
                "a scan",
                create_signal("scan", "stale_branches_oak:oak:fix/tests-ledger-across-months", "oak"),
                SignalOrigin(group="Scan stale_branches_oak", subject="fix/tests-ledger-across-months", wave=None),
            ),
            (
                "a stall",
                {**create_signal("stall", "stall:oak:oak_w57:B91", "oak"), "last_action": "2026-11-18T01:00:01Z"},
                SignalOrigin(group="Stalls", subject="B91", wave="oak_w57", last_action="2026-11-18T01:00:01Z"),
            ),
            (
                "a check run of a pull request",
                create_signal("check_run", "cr:oak:455:Dead code by vulture:448d16d9", "oak"),
                SignalOrigin(group="Check runs", subject="PR 455 · Dead code by vulture", wave=None),
            ),
            (
                "a check run of a branch",
                create_signal("check_run", "cr:oak:main:Lint: ruff:77dff3a5", "oak"),
                SignalOrigin(group="Check runs", subject="main · Lint: ruff", wave=None),
            ),
            (
                "a note",
                create_signal("note", "note:474fa40ae4db", "oak"),
                SignalOrigin(group="Notes", subject="oak", wave=None),
            ),
            (
                "a review thread of no project",
                create_signal("review_thread", "rt:PRRT_kwDO", None),
                SignalOrigin(group="Review threads", subject="-", wave=None),
            ),
            (
                "a parked order",
                create_signal("order_parked", "order_parked:prune:20261118T101500Z-a1b2c3", "oak"),
                SignalOrigin(group="order_parked", subject="oak", wave=None),
            ),
        ]
        for case, signal, expected in rows:
            with self.subTest(case=case):
                # Act
                origin = read_signal_origin(signal)

                # Assert
                self.assertEqual(origin, expected)
