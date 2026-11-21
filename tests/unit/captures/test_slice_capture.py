import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from brigade.captures.slice_capture import slice_capture
from tests.unit.captures.build_png import build_png

TWO_ROWS = 2
NONE_UP_PAETH_SUB_AVERAGE = b"\x00\x0a\x14\x02\x05\xfa\x04\x01\x02\x01\x03\x04\x03\x08\x09"


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
        self.assertEqual(_read_png(slices[0]), ((2, 2, 8, 0, 0, 0, 0), b"\x00\x0a\x14\x02\x05\xfa"))
        self.assertEqual(_read_png(slices[1]), ((2, 2, 8, 0, 0, 0, 0), b"\x00\x10\x11\x01\x03\x04"))
        self.assertEqual(_read_png(slices[2]), ((2, 1, 8, 0, 0, 0, 0), b"\x00\x09\x11"))

    def test_should_predict_from_the_left_pixel_first_when_paeth_finds_its_neighbours_equally_close(self):
        # Arrange
        self.capture.write_bytes(build_png(2, 2, b"\x00\x0a\x0b\x04\xfe\x01"))
        one_row = 1

        # Act
        slices = slice_capture(self.capture, one_row)

        # Assert
        self.assertEqual(_read_png(slices[1]), ((2, 1, 8, 0, 0, 0, 0), b"\x00\x08\x09"))

    def test_should_answer_a_capture_no_taller_than_the_bound_as_its_one_slice(self):
        # Arrange
        self.capture.write_bytes(build_png(2, 2, b"\x00\x0a\x14\x02\x05\xfa"))

        # Act
        slices = slice_capture(self.capture, TWO_ROWS)

        # Assert
        self.assertEqual(slices, [self.directory / "home-delivered-01.png"])
        self.assertEqual(_read_png(slices[0]), ((2, 2, 8, 0, 0, 0, 0), b"\x00\x0a\x14\x02\x05\xfa"))
