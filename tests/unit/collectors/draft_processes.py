import json
from pathlib import Path

from tests.unit.scripted_processes import ScriptedProcesses

SHOP = Path("/srv/shop")
SOURCE_COMMIT = "2222222222222222222222222222222222222222"
DRAFT_FIELDS = (
    ("TITLE", "the till prints the receipt of brigade/till.py"),
    ("STATUS", "draft"),
    ("SPEC", "the receipt names @DECISION.ReceiptsAreKept and the total of brigade/cart.py"),
    ("AFTER", "@TASK.B3"),
    ("RATIONALE", "brigade/cart.py:3-4 adds the line, brigade/till.py:7 prints it, brigade/shelf.py:9 stocks it"),
    ("SOURCE", "the user's ruling of 2026-11-13, e.g. on the receipt"),
)
BLAME = (
    "1111111111111111111111111111111111111111 46 46 1\n"
    "author Ada\n"
    "committer-time 1760000000\n"
    '\tSOURCE "the user\'s ruling of 2026-11-13,"\n'
    "2222222222222222222222222222222222222222 47 47 2\n"
    "author Bob\n"
    "committer-time 1760003600\n"
    '\t\t+ "e.g. on the receipt"\n'
    "2222222222222222222222222222222222222222 48 48\n"
    "\t\tREF @TASK.B3\n"
)


def script_draft_processes() -> ScriptedProcesses:
    processes = ScriptedProcesses()
    processes.answer_entities(
        SHOP,
        "TASK",
        {
            "B3": (("TITLE", "the till opens"), ("STATUS", "todo"), ("SPEC", "brigade/till.py opens the drawer")),
            "B4": (
                ("TITLE", "the receipt is kept"),
                ("STATUS", "draft"),
                ("SPEC", "brigade/till.py keeps the receipt as @DECISION.ReceiptsAreKept rules"),
            ),
            "B9": DRAFT_FIELDS,
        },
        ("STATUS!=implemented", "STATUS!=archived"),
    )
    processes.answer_json(
        ("awawa", "show", "@TASK.B9", "--json", str(SHOP)),
        {
            "file": "./corpus/tasks.awawa",
            "line": 40,
            "fields": [{"name": field, "atoms": [json.dumps(value)]} for field, value in DRAFT_FIELDS],
        },
    )
    processes.answer_json(
        ("awawa", "show", "./corpus/tasks.awawa", "--json", str(SHOP)),
        {
            "entities": [
                {"type": "TASK", "name": "B3", "lines": [{"line": 2, "field_path": ["SOURCE"]}]},
                {
                    "type": "TASK",
                    "name": "B9",
                    "lines": [
                        {"line": 40, "field_path": []},
                        {"line": 45, "field_path": ["RATIONALE"]},
                        {"line": 46, "field_path": ["SOURCE"]},
                        {"line": 47, "field_path": ["SOURCE"]},
                        {"line": 48, "field_path": ["SOURCE", "REF"]},
                    ],
                },
            ]
        },
    )
    processes.answer(("git", "blame", "--porcelain", "-L", "46,48", "HEAD", "--", "./corpus/tasks.awawa"), BLAME)
    processes.answer(
        ("git", "diff", "-U0", SOURCE_COMMIT, "HEAD", "--", "brigade/cart.py"), "@@ -1,0 +2,2 @@\n+a\n+b\n"
    )
    processes.answer(("git", "diff", "-U0", SOURCE_COMMIT, "HEAD", "--", "brigade/till.py"), "")
    processes.answer(("git", "diff", "-U0", SOURCE_COMMIT, "HEAD", "--", "brigade/shelf.py"), "@@ -9 +9 @@\n-x\n+y\n")
    return processes
