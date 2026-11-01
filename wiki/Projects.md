Answers how a git repository becomes a project brigade works on: `brigade project add`, what it discovers and guesses, and how a project is listed, shown, paused and resumed.

The projects brigade works on are `PROJECT` entities of `projects.awawa` in the operational corpus, the registry.
Every command below exits 1 naming `brigade init` until the corpus exists, and prints text or, with `--json`, a
JSON document.

## Commands

```
brigade project add <path> [--name N] [--acceptance CMD]... [--heavy CMD]... [--setup CMD]... [--force]
brigade project list
brigade project show <name>
brigade project pause <name>
brigade project resume <name>
```

## Registering a project

`project add` registers a git repository under the basename of its path, every character outside letters, digits and
`_` turned into `_`, or under `--name`. It discovers the absolute path, the `owner/name` of the `origin` remote, the
main branch (`origin/HEAD`, else the branch checked out), the folder holding the tracked `.awawa` files and the forge,
`github` for a remote on github.com. The acceptance commands and the per-worktree setup commands not given by flags are
guessed from a `package.json`, a Python project or a `Cargo.toml` at the root, and marked as guessed; the heavy suites
left to continuous integration are never guessed. A path or a name already registered is refused unless `--force`
replaces it. `pause` and `resume` set the status of a project.

## How a write reaches the registry

Every write takes the lock of the corpus repository in `$XDG_STATE_HOME/brigade/locks/`, runs `awawa fmt` on
`projects.awawa` and `awawa lint --strict` on the corpus, then commits; a failing lint restores the file and exits 1.
These commands need awawa on `PATH`.
