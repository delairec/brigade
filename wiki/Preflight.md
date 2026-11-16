What a preflight is, where it and its checks come from, how a project adds a custom one, and which deterministic checks `brigade verify preflight` runs on
the pull request of a task before any judgment.

A preflight is a named set of collectors and checks, run on demand. It declares no action of its own: each action it
needs is a collector or a check, resolved by name and reusable elsewhere. A built-in preflight is a TOML file of
`brigade/preflights/data/` naming its collectors and its checks, each with its parameters.

```
brigade preflight <name> [key=value...] [--json]   # exit 1 when a check fails
brigade preflight add <name> <collector or check> [key=value...]   # adds a step to a custom preflight, commits nothing
brigade check list [--json]                        # every check found, its name and its source
brigade verify preflight <pr> [--json]             # the built-in preflight verify-pull-request, and the size
```

`brigade preflight <name>` runs from a checkout of a registered project. It runs the collectors of the preflight, then
hands each check the parameters and the documents of the collectors, and prints the verdict and the findings of each
check, as text or, with `--json`, a JSON document. The `key=value` pairs are the parameters of every collector and
every check of the preflight, over the parameters the preflight declares. A name no preflight carries is refused.

## Where a preflight comes from

A preflight resolves by name, the first place holding it winning:

| Place     | Form                                                                                                  |
|-----------|-------------------------------------------------------------------------------------------------------|
| project   | a `PREFLIGHT` entity of the project's corpus, or `.brigade/preflights/<name>.toml` where it has none   |
| machine   | a TOML file `<config_root>/preflights/<name>.toml`                                                    |
| built-in  | a TOML file of `brigade/preflights/data/`                                                             |

A project has a corpus when it is registered in `MODE` `control` or `area`; a project in `MODE` `none`, or not
registered, keeps its custom preflights as TOML files. The two forms of a custom preflight run the same collectors and
checks. The TOML file holds `schema_version` 1, `name`, `description`, and the lists `collectors` and `checks`, each
step a `name` and its `parameters`:

```toml
schema_version = 1
name = "nightly-gate"
description = "the nightly checks of the shop"
collectors = [
    { name = "notes", parameters = { "depth" = "1" } },
]
checks = [
    { name = "coverage", parameters = {} },
]
```

The entity is named after the preflight, its hyphens as underscores; its `TITLE` is the description, each `COLLECTOR`
and `CHECK` a step, each `PARAMETER` a `key=value` pair of the step above it. The schema brigade installs in the corpus
of a project declares `SCHEMA PREFLIGHT`:

```
PREFLIGHT nightly_gate
	TITLE "the nightly checks of the shop"
	COLLECTOR "notes"
		PARAMETER "depth=1"
	CHECK "coverage"
```

## brigade preflight add

`brigade preflight add <name> <collector or check> [key=value...]` adds that collector or that check, the `key=value`
pairs its parameters, to the custom preflight `<name>` of the project, which it creates, described as
`the custom preflight <name>`, when the project holds none of that name. The step resolves as a collector first, then as
a check; a name that resolves as neither is refused before anything is written.

On a project with a corpus it writes the entity in `preflights.awawa` at the root of the corpus, runs `awawa fmt` on
that file and `awawa lint --strict` on the corpus, and restores the file from `HEAD` when the lint fails; a corpus that
declares no `PREFLIGHT` is refused, naming the type. On a project without one it writes
`.brigade/preflights/<name>.toml`, then reads it back as a preflight. It writes in the main checkout of the project
and commits nothing: `git status` shows the file, and the commit is the user's.

## Where a check comes from

A check resolves by name in the order of a collector, the first place holding it winning:

| Source     | Place                                                    |
|------------|----------------------------------------------------------|
| `project`  | an executable `.brigade/checks/<name>` of the project    |
| `machine`  | an executable `<config_root>/checks/<name>`              |
| `PATH`     | an executable `brigade-check-<name>` on `PATH`           |
| `built-in` | a module of `brigade/checks/`                            |

An executable check runs in the project, the subject on its standard input: `schema_version`, `project`, `parameters`
and `collected`, the documents of the collectors by name. It answers one JSON document, `schema_version` 1, `name`,
`verdict` `pass` or `fail` and `findings`, a list of strings; an answer that is not that document is refused, naming
the check.

## verify-pull-request

`brigade verify preflight <pr>` runs the built-in preflight `verify-pull-request`: the collector `pull-request` reads
the pull request and the trees of its head and of its base, and seven built-in checks judge them. The command adds the
size beside them. The built-in check `acceptance` is not among them: the preflight of the task branch of a project of
`FORGE none` runs it.

## The checks

| Check             | Fails when                                                                                      |
|-------------------|-------------------------------------------------------------------------------------------------|
| `ancestry`        | the head does not descend from the head of the wave's branch                                    |
| `checks`          | a check run is not completed and successful                                                     |
| `corpus`          | `awawa fmt --check .` or `awawa lint --strict .` fails on the head, read from the tree cache    |
| `promotion`       | the task is not `implemented`, its `DELIVERED_BY` is not the pull request, a `SPEC` has no `IMPL` resolving |
| `untouched_files` | a `.awawa` file of the diff changes while none of its entities does                             |
| `privacy`         | an added line matches a `PRIVATE` pattern of the project, an e-mail address or a home path, where no `PUBLIC` pattern of the project matches the whole of it |
| `body`            | the body keeps a placeholder of its template                                                    |
| `size`            | never: it reports the files, lines, packages and layers the diff touches                        |

<details><summary>What it reads</summary>

It reads the pull request a task opened as the login of `forge_accounts.cli`, and fetches its head and the wave's
branch.

</details>

## Built-in preflights

| Preflight | Collectors | Checks | What it reports |
|---|---|---|---|
| `verify-pull-request` | `pull-request` | `ancestry`, `check_runs`, `corpus_at_head`, `promotion`, `untouched_files`, `privacy`, `body` | the deterministic checks of the pull request of a task, before any judgment |
| `refinement` | `draft`, `forge-logins` | `moved_citations`, `tasks_outside_after`, `overlapping_deliverables`, `forge_logins` | on a draft task, `brigade preflight refinement task=<id>`: each `file:line` citation whose lines moved since the commit of its `SOURCE`, with where they stand now; the draft and todo tasks touching a file of its `TITLE` or `SPEC` that its `AFTER` does not name; the draft and todo tasks whose `TITLE` and `SPEC` cite a file or an entity its own cite; and the forge logins |
| `wave` | `forge-logins` | `forge_logins` | each login of `[forge_accounts]` of `config.toml` gh prints no token for; the tick runs it before it starts a wave, and a failure pauses the wave on `forge_account` before any run, until `brigade wave resume` |

A check of `refinement` fails as soon as it reports a fact: the facts are for the refinement to weigh, the preflight
judges none of them.
