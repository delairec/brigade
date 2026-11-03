import unittest

from brigade.errors import ToolNotFound
from brigade.system.stderr_masker import StderrMasker

WITHHELD = "[withheld: the PRIVATE patterns of the registered projects could not be read]"


def _mask_acme(text: str) -> str:
    return {"fatal: Acme refused": "fatal: [private] refused"}[text]


class ScrubberReaderDouble:
    def __init__(self, scrubber):
        self.scrubber = scrubber
        self.reads = 0

    def __call__(self):
        self.reads += 1
        return self.scrubber


class UnreadableScrubberDouble:
    def __init__(self):
        self.reads = 0

    def __call__(self):
        self.reads += 1
        raise ToolNotFound("awawa is not on PATH")


class StderrMaskerTest(unittest.TestCase):
    def test_should_mask_the_stderr_with_the_scrubber_it_reads(self):
        # Arrange
        masker = StderrMasker(ScrubberReaderDouble(_mask_acme))

        # Act
        masked = masker.mask("fatal: Acme refused")

        # Assert
        self.assertEqual(masked, "fatal: [private] refused")

    def test_should_read_its_scrubber_once(self):
        # Arrange
        reader = ScrubberReaderDouble(_mask_acme)
        masker = StderrMasker(reader)
        masker.mask("fatal: Acme refused")

        # Act
        masker.mask("fatal: Acme refused")

        # Assert
        self.assertEqual(reader.reads, 1)

    def test_should_read_no_scrubber_for_an_empty_stderr(self):
        # Arrange
        reader = ScrubberReaderDouble(_mask_acme)
        masker = StderrMasker(reader)
        empty_stderr = ""

        # Act
        masker.mask(empty_stderr)

        # Assert
        self.assertEqual(reader.reads, 0)

    def test_should_answer_an_empty_stderr_as_it_is(self):
        # Arrange
        masker = StderrMasker(ScrubberReaderDouble(_mask_acme))
        empty_stderr = ""

        # Act
        masked = masker.mask(empty_stderr)

        # Assert
        self.assertEqual(masked, "")


class StderrMaskerOfAnUnreadableScrubberTest(unittest.TestCase):
    def test_should_withhold_the_stderr(self):
        # Arrange
        masker = StderrMasker(UnreadableScrubberDouble())

        # Act
        masked = masker.mask("fatal: Acme refused")

        # Assert
        self.assertEqual(masked, WITHHELD)

    def test_should_not_read_its_scrubber_again(self):
        # Arrange
        reader = UnreadableScrubberDouble()
        masker = StderrMasker(reader)
        masker.mask("fatal: Acme refused")

        # Act
        masker.mask("fatal: Acme refused")

        # Assert
        self.assertEqual(reader.reads, 1)


class StderrMaskerWhileItsScrubberIsReadTest(unittest.TestCase):
    def test_should_withhold_the_stderr_of_a_process_the_reading_runs(self):
        # Arrange
        masked_during_the_reading = []

        def read_scrubber():
            masked_during_the_reading.append(masker.mask("awawa: Acme corpus unreadable"))
            return _mask_acme

        masker = StderrMasker(read_scrubber)

        # Act
        masker.mask("fatal: Acme refused")

        # Assert
        self.assertEqual(masked_during_the_reading, [WITHHELD])
