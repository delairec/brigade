from pathlib import Path

from tests.unit.captures.build_png import build_png

ONE_PIXEL_PNG = build_png(1, 1, b"\x00\x07")


def take_screenshot(request) -> tuple[int, str, str]:
    Path(request.argv[request.argv.index("--screenshot") + 1]).write_bytes(ONE_PIXEL_PNG)
    return 0, "", ""
