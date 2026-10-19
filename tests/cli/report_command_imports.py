import atexit
import json
import runpy
import sys
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT

COMMAND_MODULE_PREFIX = "brigade.commands."


def _write_command_imports(report: Path) -> None:
    report.write_text(json.dumps(sorted(name for name in sys.modules if name.startswith(COMMAND_MODULE_PREFIX))))


if __name__ == "__main__":
    atexit.register(_write_command_imports, Path(sys.argv[1]))
    sys.argv = [str(CLONE_ENTRY_POINT), *sys.argv[2:]]
    runpy.run_path(str(CLONE_ENTRY_POINT), run_name="__main__")
