Answers how to read a registered project's tree at a branch, a SHA or a worktree with `brigade corpus`, run awawa there, list its entities, and how the cache of extracted trees is bounded.

```
brigade corpus <project> --ref <branch|sha> [--json] [-- <awawa args>]
brigade corpus <project> --ref worktree:<branch> [--json] [-- <awawa args>]
brigade corpus <project> --worktree <path> [--json] [-- <awawa args>]
brigade corpus <project> --ref <ref> --type <TYPE> [--field <FIELD>] [--entity @TYPE.Name] [--json]
```

## Reading a tree

`--ref <branch|sha>` resolves the ref to a commit of the project's repository and extracts `git archive` of that
commit, the whole tree, into `$XDG_CACHE_HOME/brigade/refs/<project>/<sha>/`, once: a SHA already there is read from
the cache. `--ref worktree:<branch>` reads in place the worktree where that branch is checked out, `--worktree <path>`
the worktree at that path, a detached HEAD included; uncommitted edits are visible. The command prints the project,
the ref, the SHA, the kind (`archive` or `worktree`) and the root of the tree, as text or, with `--json`, a JSON
document; an unknown project, a ref that resolves to no commit, and a branch or a path no worktree holds exit 1.

## Running awawa on the tree

Given `-- <awawa args>`, it runs awawa with those arguments at the root of the tree instead, and passes its stdout,
its stderr and its exit code through unchanged, after one stderr line naming the SHA it read.

## Listing entities

Given `--type <TYPE>`, the document also lists the entities of that type with their status, their file and their line,
the types of the corpus, and `awawa_web`, `http://127.0.0.1:7878/` when `brigade doctor` finds awawa-web on the PATH,
null otherwise; each entity carries `ide_link`, the key `ide_link` of `config.toml` with `{path}` and `{line}` replaced,
null when the key is empty. `--field <FIELD>` adds the board: the entities grouped by the values of that field, those
without it in a column of their own. `--entity @TYPE.Name` adds what that entity reaches and what references it.
`--field` or `--entity` without `--type` exits 1.

## The cache

The cache holds at most `refs_cache_mb` of `config.toml`, 1024 by default: each read marks its SHA used, and after
each extraction the least recently read SHAs are removed until the cache is under that bound. The reuse of a cached
tree, the placing of an extracted one and the removals run under the lock `$XDG_STATE_HOME/brigade/locks/refs-cache.lock`;
the reading of a tree after brigade printed its root does not, so another `brigade corpus` that prunes the cache can
remove a tree still read through `-- <awawa args>` when the bound is too tight to hold both.
