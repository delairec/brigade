How a git repository becomes a project brigade works on with `brigade project add`, what it discovers and guesses,
and how a project is listed, shown, paused and resumed.

## Commands

```
brigade project add <path> [--name N] [--acceptance CMD]... [--heavy CMD]... [--setup CMD]... [--force]
brigade project list
brigade project show <name>
brigade project pause <name>     # pause and resume set the status of a project
brigade project resume <name>
```

Every command prints text or, with `--json`, a JSON document.

## What `project add` discovers

A project is a `PROJECT` entity of `projects.awawa` in the operational corpus, the registry. `project add` registers
a git repository under the basename of its path, every character outside letters, digits and `_` turned into `_`, or
under `--name`.

| What | Read from |
|---|---|
| the absolute path | the path given |
| the `owner/name` | the `origin` remote |
| the main branch | `origin/HEAD`, else the branch checked out |
| the corpus folder | the folder holding the tracked `.awawa` files |
| the forge | `github` for a remote on github.com |
| the acceptance commands and the per-worktree setup commands not given by flags | guessed from a `package.json`, a Python project or a `Cargo.toml` at the root, and marked as guessed |

The heavy suites left to continuous integration (`--heavy`) are never guessed.

> **Watch out:** every command exits 1 naming `brigade init` until the operational corpus exists, and needs awawa on
> `PATH`.

> **Watch out:** a path or a name already registered is refused unless `--force` replaces it.

<details><summary>How a write reaches the registry</summary>

Every write:

1. takes the lock of the corpus repository in `$XDG_STATE_HOME/brigade/locks/`;
2. runs `awawa fmt` on `projects.awawa` and `awawa lint --strict` on the corpus;
3. commits.

A failing lint restores the file and exits 1.

</details>
