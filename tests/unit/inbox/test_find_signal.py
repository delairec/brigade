import unittest

from brigade.errors import BrigadeError
from brigade.inbox.find_signal import find_signal
from brigade.inbox.read_inbox import Signal

NOTE_ON_OAK = Signal(
    id="a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
    fingerprint="note:474fa40ae4db",
    kind="note",
    project="oak",
    count=1,
    age_s=60,
    status="new",
    evidence={"text": "fix the flaky test"},
)
NOTE_ON_ASH = Signal(
    id="a4a5e000d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
    fingerprint="note:000000000000",
    kind="note",
    project="ash",
    count=1,
    age_s=60,
    status="dismissed",
    evidence={"text": "prune the branches"},
)
INBOX = (NOTE_ON_OAK, NOTE_ON_ASH)


class FindSignalTest(unittest.TestCase):
    def test_should_find_the_one_signal_the_prefix_names(self):
        # Act
        signal = find_signal(INBOX, "a4a5f")

        # Assert
        self.assertEqual(signal, NOTE_ON_OAK)

    def test_should_refuse_a_prefix_no_signal_matches(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            find_signal(INBOX, "ffff")

        # Assert
        self.assertEqual(str(refusal.exception), "no signal of the inbox has an id starting with ffff")

    def test_should_refuse_a_prefix_several_signals_match_listing_them(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            find_signal(INBOX, "a4a5")

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "2 signals of the inbox have an id starting with a4a5:"
            " a4a5f46 note:474fa40ae4db, a4a5e00 note:000000000000",
        )

    def test_should_refuse_a_prefix_shorter_than_4_characters(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            find_signal(INBOX, "a4a")

        # Assert
        self.assertEqual(str(refusal.exception), "the id a4a is shorter than 4 characters")
