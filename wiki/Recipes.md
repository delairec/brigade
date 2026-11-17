How to write a recipe, from the example brigade ships: `pr-usage-report`, the usage report of one reviewed pull
request, committed on its branch before the merge.

A recipe is a kind of work, written once; an order is an instance of it, recorded by `brigade order new` with the
values of its params. A recipe is a TOML file of steps. It names no client and no model: the judge step names a slot,
and the slot finds its role (see [Roles](Roles.md)).

```
brigade recipe list                                  # every recipe found, its name and its source
brigade recipe show pr-usage-report                  # the recipe as it resolves, and its source
brigade recipe lint pr-usage-report                  # its schema, its names and its params
brigade order new pr-usage-report pr=42              # record an order of it and run it once
```

## Where a recipe lives

A recipe resolves by name, the first place holding it winning; `brigade recipe list` prints them in that order:

| Place     | Form                                                       |
|-----------|------------------------------------------------------------|
| project   | `.brigade/recipes/<name>.toml` in the project's repository |
| machine   | `recipes/<name>.toml` in the configuration directory       |
| built-in  | `brigade/recipes/data/<name>.toml`, shipped with brigade   |

To write a recipe of your own, copy `brigade/recipes/data/pr-usage-report.toml` into the project or the machine
place, under the name of your recipe, and change its steps.

## The example, line by line

```toml
schema_version = 1
name = "pr-usage-report"
description = "the usage report of one reviewed pull request, committed on its branch before the merge"
params = ["pr"]
max_wall = 60
steps = [
    { kind = "collect", collector = "ledger" },
    { kind = "collect", collector = "pr-threads" },
    { kind = "collect", collector = "corpus" },
    { kind = "gate", preflight = "pr-reviewed", parameters = { pr = "{pr}" } },
    { kind = "judge", slot = "report", procedure = "pr-usage-report", answer = "RESULT" },
    { kind = "output", output = "pr-file:{pr}:docs/usage-reports/pull-requests/{pr}.md" },
]
```

- `params` names the values an order gives as `key=value`: `brigade order new pr-usage-report pr=42`. A step uses one
  as `{pr}`; `{project}` is always available. A placeholder naming no param is refused by `brigade recipe lint`.
- `max_wall` is the time, in minutes, a run of the order may take.
- The steps run in order, each result a file under `runs/<id>/steps/`, and each recorded in the ledger as
  `step.done`. A step that fails parks the order, unless its `on_fail` says `skip`, `stop` or `retry:N`; a parked
  order resumes at its first undone step with `brigade order run <order>`.

## The kinds of step

| Kind      | Keys                                 | What it does                                                                 |
|-----------|--------------------------------------|------------------------------------------------------------------------------|
| `collect` | `collector`, `parameters`            | runs a collector, deterministic, no run of an agent; see [Studies](Studies.md) |
| `gate`    | `preflight`, `parameters`            | runs a named preflight and fails the step when one of its checks fails; see [Preflight](Preflight.md) |
| `judge`   | `slot`, `procedure`, `answer`        | runs the procedure as the slot, which writes an answer of the type named     |
| `output`  | `output`                             | publishes the answer of the judge step                                       |
| `command` | `argv`                               | runs a command; never the binary of the configured client                    |

Only the judge step runs an agent: in the example, the three collectors and the gate leave no run in the ledger, and
the run of the judge step is the only `run.finished`.

## The gate

`pr-reviewed` is a built-in preflight, `brigade/preflights/data/pr-reviewed.toml`: it collects `pr-list` and runs the
check `reviewed`, which fails on a pull request no review was submitted on. The step hands it `pr = "{pr}"`, filled
from the order. A gate refuses work before any agent runs: an order of an unreviewed pull request parks at its gate,
and no report is judged.

## The judge step

`procedure` names a procedure file, read from `brigade/runs/data/procedures/<name>.md` and then from `procedures/` of
the instructions corpus; its front matter declares its `capabilities`. The procedure of the example reads the
documents of the collectors with `brigade order context <run> --json`, fills the prose fields of the RESULT entity
brigade prepared, and hands it back with `brigade order answer <run> --file <path>`, which validates it against the
schema of its type. `slot` is one of the slots of [Roles](Roles.md); `report` is the slot of a reporting run.

## The output

| Output                     | Publishes the answer                                                     |
|----------------------------|--------------------------------------------------------------------------|
| `pr-file:<n>:<path>`       | as a file committed and pushed on the head branch of the pull request `<n>` |
| `file:<path>`              | as a file                                                                |
| `entity:<TYPE>`            | as an entity appended to the registry                          |
| `issue`                    | as an issue of the project's forge                                       |
| `inbox`                    | as a signal of the inbox                                                 |
| `<name>`                   | to the executable `brigade-output-<name>` found on PATH                  |

`pr-file` needs a project with a forge. In the example, the report lands at
`docs/usage-reports/pull-requests/<n>.md` on the branch of the pull request it judges, before its merge.
