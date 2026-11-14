How a run of the `rebase` slot puts the branch of a task back on its base after a conflict, with
`brigade rebase context` and `brigade rebase done`.

```
brigade rebase context [<pr>]    # the branch, its base and the files in conflict
brigade rebase context --head <commit> [--into <main>]   # the branch repaired, its red commit and what failed
brigade rebase done <pr>         # check that the rebased head descends from its base
brigade rebase pr --into <main>  # push the branch repairing a red main branch and open its pull request
```

Both run from the worktree of the task whose rebase conflicted, in a run of the `rebase` slot.

- `rebase context` prints the branch of the pull request, its base, the branch the `wave.started` of its wave names,
  and the files `git merge-tree` reports in conflict between the head and `origin/<base>`.
- `rebase done` fetches both branches, checks that the head descends from `origin/<base>` and prints it; it pushes
  nothing. The run then pushes the branch with `brigade task push`, once `brigade task check` passed on that head.

> **Watch out:** `rebase done` refuses a head that does not descend from `origin/<base>`: exit 1, and the run pushes
> nothing.

<details><summary>A task with no pull request yet</summary>

Without `<pr>`, `rebase context` reads the task and its wave from the branch of the worktree, and the conflicts against
`origin/<base>` on a project of `FORGE github`, against the local `<base>` otherwise.

</details>

<details><summary>A red head repaired</summary>

A run of the `rebase` slot launched on a red head rebases nothing and takes the arguments `branch` and `head`, the red
commit, with no `base`:

- With `branch` and `head` alone, the branch of a milestone red at that head is repaired in place in its worktree: the
  run commits `fix(<scope>): <what the repair restores>` and pushes the branch with `--force-with-lease` once its tests
  pass.
- With `into` as well, the main branch of the project red at that head is repaired on the branch
  `fix/repair-<main>-<commit>` cut from it: the run pushes that branch and opens its pull request into the main branch
  with `brigade rebase pr --into <main>`, which the user merges. The command pushes and opens it under the login
  `[forge_accounts]` binds to the `rebase` slot, its title the subject of the head commit, and records that login in
  the ledger event `repair.pr_opened`.

`rebase context --head <commit>` prints the branch of the worktree, the red commit and each command that failed at
it, read from the check runs of the forge on that commit, on the main branch with `--into`, or from the record the
tick kept for it.

</details>
