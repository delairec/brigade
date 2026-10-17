import unittest
from datetime import UTC, datetime

from brigade.studies.read_live_study_runs import LiveStudyRun
from brigade.tick.build_snapshot import Snapshot, StudyFacts


class SnapshotTest(unittest.TestCase):
    def test_should_carry_now_as_an_utc_instant_in_its_document(self):
        # Arrange
        snapshot = Snapshot(now=datetime(2026, 10, 6, 12, 0, 7, 250000, tzinfo=UTC))

        # Act
        document = snapshot.to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "now": "2026-10-06T12:00:07Z",
                "waves": [],
                "projects": [],
                "planned": [],
                "studies": [],
                "live_study_runs": [],
                "study_runs": 2,
            },
        )

    def test_should_carry_the_studies_and_their_live_runs_in_its_document(self):
        # Arrange
        weekly = StudyFacts(
            name="weekly",
            slot="report",
            every="daily@09:00",
            status="active",
            last_started=datetime(2026, 10, 5, 7, 0, 2, tzinfo=UTC),
            parked=False,
        )
        live = LiveStudyRun(study="weekly", run="20261006T110000Z-a1b2c3")
        snapshot = Snapshot(now=datetime(2026, 10, 6, 12, 0, tzinfo=UTC), studies=(weekly,), live_study_runs=(live,))

        # Act
        document = snapshot.to_document()

        # Assert
        self.assertEqual(
            (document["studies"], document["live_study_runs"]),
            (
                [
                    {
                        "study": "weekly",
                        "slot": "report",
                        "every": "daily@09:00",
                        "status": "active",
                        "last_started": "2026-10-05T07:00:02Z",
                        "parked": False,
                    }
                ],
                [{"study": "weekly", "run": "20261006T110000Z-a1b2c3"}],
            ),
        )
