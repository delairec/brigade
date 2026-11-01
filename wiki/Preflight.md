Which deterministic checks `brigade verify preflight` runs on the pull request of a task before any judgment, and when
each fails.

```
brigade verify preflight <pr> [--json]    # exit 1 when a check fails
```

It runs from a checkout of a registered project. It prints one entry per check, its verdict `pass`, `fail` or `info`
and its findings, as text or, with `--json`, a JSON document.

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
