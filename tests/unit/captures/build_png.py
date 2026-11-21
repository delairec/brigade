import struct
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
GRAYSCALE = 0
EIGHT_BITS = 8


def _build_chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def build_png(width: int, height: int, scanlines: bytes) -> bytes:
    header = struct.pack(">IIBBBBB", width, height, EIGHT_BITS, GRAYSCALE, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + _build_chunk(b"IHDR", header)
        + _build_chunk(b"IDAT", zlib.compress(scanlines))
        + _build_chunk(b"IEND", b"")
    )
