import json

from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT
from tests.cli.test_run_list_and_show import RunsTestCase

HANDED_OVER_RESULT = {**DONE_RESULT, "outcome": "handed_over"}
PROGRESS_OF_THE_FIRST_SEGMENT = 'progress = "- the first segment is done"\n'


class BrigadeRunNoteBetweenTwoSegmentsTest(RunsTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT + self.hold_the_client() + PROGRESS_OF_THE_FIRST_SEGMENT)
        self.record("builder", HANDED_OVER_RESULT)
        (self.recordings / "builder.resumed.json").write_text(json.dumps(DONE_RESULT))

    def note_the_run_while_its_first_segment_is_held(self):
        run_id = self.run_deliver("--detach").stdout.strip()
        brigade_pid = self.read_run_pid(run_id)
        self.wait_for_client(brigade_pid)
        noted = self.run_brigade("run", "note", run_id, "the corpus of main holds two L016 errors")
        self.hold.unlink()
        self.wait_for_exit(brigade_pid)
        return run_id, noted

    def test_should_say_the_note_waits_for_the_next_segment_of_the_run(self):
        # Act
        run_id, noted = self.note_the_run_while_its_first_segment_is_held()

        # Assert
        self.assertEqual(noted.returncode, 0, noted.stderr)
        self.assertEqual(
            noted.stdout,
            f"noted run {run_id}: the note waits for the next segment of the run,"
            " a segment already launched taking no input\n",
        )

    def test_should_carry_the_note_in_the_brief_of_the_second_segment(self):
        # Act
        run_id, _noted = self.note_the_run_while_its_first_segment_is_held()

        # Assert
        self.assertRegex(
            (self.runs / run_id / "segments" / "2" / "brief.md").read_text(encoding="utf-8"),
            r"^# Progress so far\n\n- the first segment is done\n\n"
            r"# Notes handed to the run\n\n- \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z: the corpus of main holds two L016"
            r" errors\n\n# Procedure deliver\n",
        )
