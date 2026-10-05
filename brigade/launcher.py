import sys

from brigade.python_floor import describe_python_floor_breach


def launch() -> None:
    breach = describe_python_floor_breach(tuple(sys.version_info[:3]))
    if breach is not None:
        sys.stderr.write(breach + "\n")
        sys.exit(1)
    from brigade.cli import main

    sys.exit(main(sys.argv[1:]))
