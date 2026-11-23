import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from brigade.captures.slice_capture import slice_capture
from brigade.errors import BrigadeError
from tests.unit.captures.build_png import GRAYSCALE, build_png

TWO_ROWS = 2
NONE_UP_PAETH_SUB_AVERAGE = (
    b"\x00\x0a\x14\x1e\x28\x32\x3c\x46\x50"
    b"\x02\x01\x01\x01\xe2\xd9\x02\xde\xbb"
    b"\x04\x03\x00\xfb\xfe\x01\x02\x03\x04"
    b"\x01\x09\x08\x07\x06\x01\x02\x03\x04"
    b"\x03\x02\x04\x06\x08\x0a\x0c\x0e\x10"
)
NONE_UP = b"\x00\x0a\x14\x1e\x28\x32\x3c\x46\x50\x02\x01\x01\x01\xe2\xd9\x02\xde\xbb"


def _read_png(path: Path) -> tuple[tuple[int, ...], bytes]:
    png = path.read_bytes()
    header = struct.unpack(">IIBBBBB", png[16:29])
    (length,) = struct.unpack(">I", png[33:37])
    return header, zlib.decompress(png[41 : 41 + length])


class SliceCaptureTest(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.capture = self.directory / "home-delivered.png"

    def test_should_cut_a_capture_taller_than_the_bound_into_ordered_slices(self):
        # Arrange
        self.capture.write_bytes(build_png(2, 5, NONE_UP_PAETH_SUB_AVERAGE))

        # Act
        slices = slice_capture(self.capture, TWO_ROWS)

        # Assert
        self.assertEqual(
            slices,
            [
                self.directory / "home-delivered-01.png",
                self.directory / "home-delivered-02.png",
                self.directory / "home-delivered-03.png",
            ],
        )

    def test_should_keep_every_pixel_of_the_capture_each_slice_opening_on_a_row_it_decodes_alone(self):
        # Arrange
        self.capture.write_bytes(build_png(2, 5, NONE_UP_PAETH_SUB_AVERAGE))

        # Act
        slices = slice_capture(self.capture, TWO_ROWS)

        # Assert
        self.assertEqual(
            _read_png(slices[0]),
            (
                (2, 2, 8, 6, 0, 0, 0),
                b"\x00\x0a\x14\x1e\x28\x32\x3c\x46\x50\x02\x01\x01\x01\xe2\xd9\x02\xde\xbb",
            ),
        )
        self.assertEqual(
            _read_png(slices[1]),
            (
                (2, 2, 8, 6, 0, 0, 0),
                b"\x00\x0e\x15\x1a\x08\x0f\x40\x22\x0c\x01\x09\x08\x07\x06\x01\x02\x03\x04",
            ),
        )
        self.assertEqual(_read_png(slices[2]), ((2, 1, 8, 6, 0, 0, 0), b"\x00\x06\x08\x09\x0b\x12\x15\x17\x1a"))

    def test_should_predict_from_the_pixel_above_rather_than_the_one_above_left_when_both_are_as_close(self):
        # Arrange
        one_row = 1
        above_then_predicted = b"\x00\x01\x01\x01\x01\x03\x03\x03\x03\x04\xff\xff\xff\xff\x00\x00\x00\x00"
        self.capture.write_bytes(build_png(2, 2, above_then_predicted))

        # Act
        slices = slice_capture(self.capture, one_row)

        # Assert
        self.assertEqual(_read_png(slices[1]), ((2, 1, 8, 6, 0, 0, 0), b"\x00\x00\x00\x00\x00\x03\x03\x03\x03"))

    def test_should_answer_a_capture_no_taller_than_the_bound_as_its_one_slice(self):
        # Arrange
        self.capture.write_bytes(build_png(2, 2, NONE_UP))

        # Act
        slices = slice_capture(self.capture, TWO_ROWS)

        # Assert
        self.assertEqual(slices, [self.directory / "home-delivered-01.png"])
        self.assertEqual(_read_png(slices[0]), ((2, 2, 8, 6, 0, 0, 0), NONE_UP))

    def test_should_refuse_a_capture_firefox_does_not_write_as_8_bit_rgba(self):
        # Arrange
        self.capture.write_bytes(build_png(2, 1, b"\x00\x0a\x14", colour=GRAYSCALE))

        # Act
        with self.assertRaises(BrigadeError) as raised:
            slice_capture(self.capture, TWO_ROWS)

        # Assert
        self.assertEqual(
            str(raised.exception),
            f"{self.capture} is a PNG of colour type 0 at 8 bits: brigade slices the 8-bit RGBA PNG Firefox writes",
        )
