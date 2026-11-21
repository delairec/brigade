import struct
import zlib
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
CHUNK_HEAD = struct.Struct(">I4s")
CHUNK_CHECKSUM = struct.Struct(">I")
CHUNK_FRAME = CHUNK_HEAD.size + CHUNK_CHECKSUM.size
HEADER = struct.Struct(">IIBBBBB")
HEADER_KIND = b"IHDR"
DATA_KIND = b"IDAT"
END_KIND = b"IEND"
CHANNELS = {0: 1, 2: 3, 4: 2, 6: 4}
BITS_PER_BYTE = 8
DECODED_ALONE = (0, 1)
NO_FILTER = b"\x00"
BYTE_MASK = 0xFF


def _read_chunks(png: bytes) -> list[tuple[bytes, bytes]]:
    chunks = []
    position = len(PNG_SIGNATURE)
    while position < len(png):
        length, kind = CHUNK_HEAD.unpack_from(png, position)
        start = position + CHUNK_HEAD.size
        chunks.append((kind, png[start : start + length]))
        position += length + CHUNK_FRAME
    return chunks


def _write_chunk(kind: bytes, body: bytes) -> bytes:
    return CHUNK_HEAD.pack(len(body), kind) + body + CHUNK_CHECKSUM.pack(zlib.crc32(kind + body))


def _predict_paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    return min(
        (abs(estimate - left), 0, left), (abs(estimate - up), 1, up), (abs(estimate - upper_left), 2, upper_left)
    )[2]


def _predict(kind: int, left: int, up: int, upper_left: int) -> int:
    return (0, left, up, (left + up) // 2, _predict_paeth(left, up, upper_left))[kind]


def _unfilter(row: bytes, prior: bytes, pixel_bytes: int) -> bytes:
    shown = bytearray(pixel_bytes)
    above = bytes(pixel_bytes) + prior
    for index, value in enumerate(row[1:]):
        predicted = _predict(row[0], shown[index], above[index + pixel_bytes], above[index])
        shown.append((value + predicted) & BYTE_MASK)
    return bytes(shown[pixel_bytes:])


def _open_slice(rows: list[bytes], start: int, pixel_bytes: int) -> bytes:
    anchor = next((index for index in range(start, 0, -1) if rows[index][0] in DECODED_ALONE), 0)
    shown = bytes(len(rows[start]) - 1)
    for row in rows[anchor : start + 1]:
        shown = _unfilter(row, shown, pixel_bytes)
    return NO_FILTER + shown


def slice_capture(png: Path, bound: int) -> list[Path]:
    chunks = _read_chunks(png.read_bytes())
    width, height, depth, colour, *methods = HEADER.unpack(chunks[0][1])
    bits = CHANNELS[colour] * depth
    stride = (width * bits + BITS_PER_BYTE - 1) // BITS_PER_BYTE + 1
    scanlines = zlib.decompress(b"".join(body for kind, body in chunks if kind == DATA_KIND))
    rows = [scanlines[index * stride : (index + 1) * stride] for index in range(height)]
    pixel_bytes = max(1, bits // BITS_PER_BYTE)
    slices = []
    for rank, start in enumerate(range(0, height, bound), start=1):
        kept = [_open_slice(rows, start, pixel_bytes), *rows[start + 1 : start + bound]]
        header = HEADER.pack(width, len(kept), depth, colour, *methods)
        sliced = png.with_name(f"{png.stem}-{rank:02d}.png")
        sliced.write_bytes(
            PNG_SIGNATURE
            + _write_chunk(HEADER_KIND, header)
            + _write_chunk(DATA_KIND, zlib.compress(b"".join(kept)))
            + _write_chunk(END_KIND, b"")
        )
        slices.append(sliced)
    return slices
