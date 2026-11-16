What a preflight is, where its checks come from, and which deterministic checks `brigade verify preflight` runs on
the pull request of a task before any judgment.

A preflight is a named set of collectors and checks, run on demand. It declares no action of its own: each action it
needs is a collector or a check, resolved by name and reusable elsewhere. A built-in preflight is a TOML file of
`brigade/preflights/data/` naming its collectors and its checks, each with its parameters.

```
brigade preflight <name> [key=value...] [--json]   # exit 1 when a check fails
brigade check list [--json]                        # every check found, its name and its source
brigade verify preflight <pr> [--json]             # the built-in preflight verify-pull-request, and the size
```

`brigade preflight <name>` runs from a checkout of a registered project. It runs the collectors of the preflight, then
hands each check the parameters and the documents of the collectors, and prints the verdict and the findings of each
check, as text or, with `--json`, a JSON document. The `key=value` pairs are the parameters of every collector and
every check of the preflight, over the parameters the preflight declares. A name no preflight carries is refused.

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
