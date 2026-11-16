REVIEW_RECIPE_TOML = """\
schema_version = 1
name = "review"
description = "review a pull request"
params = ["pr"]
max_wall = 30

[[steps]]
kind = "collect"
collector = "pull-request"
parameters = { number = "{pr}", project = "{project}" }

[[steps]]
kind = "gate"
preflight = "verify-pull-request"
on_fail = "retry:2"

[[steps]]
kind = "command"
argv = ["uvx", "ruff", "check", "."]

[[steps]]
kind = "judge"
slot = "review"
procedure = "review-pr"
answer = "REPORT"

[[steps]]
kind = "output"
output = "inbox"
"""

REVIEW_RECIPE_ENTITY = {
    "type": "RECIPE",
    "name": "review",
    "fields": [
        {"name": "DESC", "atoms": ['"review a pull request"'], "fields": []},
        {"name": "SCHEMA_VERSION", "atoms": ["1"], "fields": []},
        {"name": "PARAM", "atoms": ['"pr"'], "fields": []},
        {"name": "MAX_WALL", "atoms": ["30"], "fields": []},
        {
            "name": "STEP",
            "atoms": ["collect"],
            "fields": [
                {"name": "COLLECTOR", "atoms": ['"pull-request"'], "fields": []},
                {"name": "PARAMETER", "atoms": ['"number={pr}"'], "fields": []},
                {"name": "PARAMETER", "atoms": ['"project={project}"'], "fields": []},
            ],
        },
        {
            "name": "STEP",
            "atoms": ["gate"],
            "fields": [
                {"name": "PREFLIGHT", "atoms": ['"verify-pull-request"'], "fields": []},
                {"name": "ON_FAIL", "atoms": ['"retry:2"'], "fields": []},
            ],
        },
        {
            "name": "STEP",
            "atoms": ["command"],
            "fields": [
                {"name": "ARGV", "atoms": ['"uvx"'], "fields": []},
                {"name": "ARGV", "atoms": ['"ruff"'], "fields": []},
                {"name": "ARGV", "atoms": ['"check"'], "fields": []},
                {"name": "ARGV", "atoms": ['"."'], "fields": []},
            ],
        },
        {
            "name": "STEP",
            "atoms": ["judge"],
            "fields": [
                {"name": "SLOT", "atoms": ['"review"'], "fields": []},
                {"name": "PROCEDURE", "atoms": ['"review-pr"'], "fields": []},
                {"name": "ANSWER", "atoms": ['"REPORT"'], "fields": []},
            ],
        },
        {"name": "STEP", "atoms": ["output"], "fields": [{"name": "OUTPUT", "atoms": ['"inbox"'], "fields": []}]},
        {"name": "SOURCE", "atoms": ['"the review the user asked for"'], "fields": []},
    ],
}

REVIEW_RECIPE_DOCUMENT = {
    "schema_version": 1,
    "name": "review",
    "description": "review a pull request",
    "params": ["pr"],
    "max_wall": 30,
    "steps": [
        {"kind": "collect", "collector": "pull-request", "parameters": {"number": "{pr}", "project": "{project}"}},
        {"kind": "gate", "preflight": "verify-pull-request", "on_fail": "retry:2"},
        {"kind": "command", "argv": ["uvx", "ruff", "check", "."]},
        {"kind": "judge", "slot": "review", "procedure": "review-pr", "answer": "REPORT"},
        {"kind": "output", "output": "inbox"},
    ],
}
