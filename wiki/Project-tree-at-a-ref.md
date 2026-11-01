How to read a registered project's tree at a branch, a SHA or a worktree with `brigade corpus`, run awawa there, list
its entities, and how the cache of extracted trees is bounded.

## Commands

```
brigade corpus <project> --ref <branch|sha> [--json] [-- <awawa args>]
brigade corpus <project> --ref worktree:<branch> [--json] [-- <awawa args>]
brigade corpus <project> --worktree <path> [--json] [-- <awawa args>]
brigade corpus <project> --ref <ref> --type <TYPE> [--field <FIELD>] [--entity @TYPE.Name] [--json]
```

| Option | Reads |
|---|---|
| `--ref <branch\|sha>` | `git archive` of that commit, the whole tree, extracted once into `$XDG_CACHE_HOME/brigade/refs/<project>/<sha>/` |
| `--ref worktree:<branch>` | in place, the worktree where that branch is checked out; uncommitted edits are visible |
| `--worktree <path>` | in place, the worktree at that path, a detached HEAD included; uncommitted edits are visible |

The command prints the project, the ref, the SHA, the kind (`archive` or `worktree`) and the root of the tree, as text
or, with `--json`, a JSON document.

## Running awawa on the tree

Given `-- <awawa args>`, it runs awawa with those arguments at the root of the tree instead, and passes its stdout,
its stderr and its exit code through unchanged, after one stderr line naming the SHA it read.

```
brigade corpus <project> --ref main -- status .
```

## Listing entities

| Option | Adds to the document |
|---|---|
| `--type <TYPE>` | the entities of that type with their status, their file and their line, and the types of the corpus |
| `--field <FIELD>` | the board: the entities grouped by the values of that field, those without it in a column of their own |
| `--entity @TYPE.Name` | what that entity reaches and what references it |

> **Watch out:** `--field` or `--entity` without `--type` exits 1.

## Details and edge cases

<details><summary>Errors</summary>

An unknown project, a ref that resolves to no commit, and a branch or a path no worktree holds exit 1.

</details>

<details><summary>Links in the <code>--type</code> document</summary>

- `awawa_web` is `http://127.0.0.1:7878/` when `brigade doctor` finds awawa-web on the PATH, null otherwise.
- Each entity carries `ide_link`, the key `ide_link` of `config.toml` with `{path}` and `{line}` replaced, null when the
  key is empty.

</details>

<details><summary>The cache of extracted trees</summary>

- A SHA already in the cache is read from it.
- The cache holds at most `refs_cache_mb` of `config.toml`, 1024 by default: each read marks its SHA used, and after
  each extraction the least recently read SHAs are removed until the cache is under that bound.
- The reuse of a cached tree, the placing of an extracted one and the removals run under the lock
  `$XDG_STATE_HOME/brigade/locks/refs-cache.lock`. The reading of a tree after brigade printed its root does not, so
  another `brigade corpus` that prunes the cache can remove a tree still read through `-- <awawa args>` when the bound
  is too tight to hold both.

</details>
