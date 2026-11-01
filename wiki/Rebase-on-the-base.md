How a run of the `rebase` slot puts the branch of a task back on its base after a conflict, with
`brigade rebase context` and `brigade rebase done`.

```
brigade rebase context [<pr>]    # the branch, its base and the files in conflict
brigade rebase done <pr>         # push the rebased head onto the branch
```

Both run from the worktree of the task whose rebase conflicted, in a run of the `rebase` slot.

- `rebase context` prints the branch of the pull request, its base, the branch the `wave.started` of its wave names,
  and the files `git merge-tree` reports in conflict between the head and `origin/<base>`.
- `rebase done` fetches both branches and pushes the head onto the branch with `--force-with-lease` on the remote head
  it fetched, under the account of the run, then prints the head pushed.

> **Watch out:** `rebase done` refuses a head that does not descend from `origin/<base>`: exit 1, and nothing is
> pushed.

<details><summary>A task with no pull request yet</summary>

Without `<pr>`, `rebase context` reads the task and its wave from the branch of the worktree, and the conflicts against
`origin/<base>` on a project of `FORGE github`, against the local `<base>` otherwise.

</details>
