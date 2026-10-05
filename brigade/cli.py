import argparse
import json

from brigade import VERSION


def _create_parser():
    parser = argparse.ArgumentParser(prog="brigade")
    parser.add_argument("--version", action="store_true", help="print the version of brigade")
    parser.add_argument("--json", action="store_true", help="print the output as a JSON document")
    return parser


def _describe_version(as_json):
    if as_json:
        return json.dumps({"schema_version": 1, "version": VERSION})
    return f"brigade {VERSION}"


def main(arguments):
    parser = _create_parser()
    options = parser.parse_args(arguments)
    if not options.version:
        parser.error("no option given")
    print(_describe_version(options.json))
    return 0
