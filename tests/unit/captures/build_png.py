import struct
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
TRUECOLOUR_WITH_ALPHA = 6
GRAYSCALE = 0
TRUECOLOUR = 2
EIGHT_BITS = 8
NOT_INTERLACED = 0
DATA_CHUNK_BYTES = 16


def _build_chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def build_png(
    width: int,
    height: int,
    scanlines: bytes,
    colour: int = TRUECOLOUR_WITH_ALPHA,
    depth: int = EIGHT_BITS,
    interlace: int = NOT_INTERLACED,
) -> bytes:
    header = struct.pack(">IIBBBBB", width, height, depth, colour, 0, 0, interlace)
    compressed = zlib.compress(scanlines)
    data_chunks = b"".join(
        _build_chunk(b"IDAT", compressed[start : start + DATA_CHUNK_BYTES])
        for start in range(0, len(compressed), DATA_CHUNK_BYTES)
    )
    return PNG_SIGNATURE + _build_chunk(b"IHDR", header) + data_chunks + _build_chunk(b"IEND", b"")
