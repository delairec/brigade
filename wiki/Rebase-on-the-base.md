Answers how a run of the `rebase` slot puts the branch of a task back on its base after a conflict, with `brigade rebase context` and `brigade rebase done`.

```
brigade rebase context [<pr>]
brigade rebase done <pr>
```

Both run from the worktree of the task whose rebase conflicted, in a run of the `rebase` slot. `rebase context` prints
the branch of the pull request, its base, the branch the `wave.started` of its wave names, and the files `git
merge-tree` reports in conflict between the head and `origin/<base>`; without `<pr>`, for a task that has no pull
request yet, it reads the task and its wave from the branch of the worktree, and the conflicts against
`origin/<base>` on a project of `FORGE github`, against the local `<base>` otherwise. `rebase done` fetches both branches, refuses a
head that does not descend from `origin/<base>`, exit 1, and pushes nothing; otherwise it pushes the head onto the
branch with `--force-with-lease` on the remote head it fetched, under the account of the run, and prints the head
pushed.
