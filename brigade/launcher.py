import sys

from brigade.python_floor import refuse_python_below_floor


def launch() -> None:
    refuse_python_below_floor(tuple(sys.version_info[:3]))
    from brigade.cli import main

    sys.exit(main(sys.argv[1:]))
