Rebuild @TASK.$task of @PROJECT.$project, in the wave $wave, to its entity as amended on $base since its pull request #$pr opened.

- Pull request: #$pr, kept: no second one is opened.
- Base branch: $base.
- Worktree: $worktree, on the branch $task_branch, handed over as it stands, uncommitted changes included.

Put the branch on the head of $base, by a rebase or by a reset onto that head and a new implementation, and deliver on it the entity as it stands on $base. Push the branch with `git push --force-with-lease` and rewrite the body of the pull request #$pr to describe the head pushed, instead of opening a pull request.

The entity on the head of the pull request #$pr:

```
$on_pull_request
```

The entity on $base:

```
$on_wave
```
