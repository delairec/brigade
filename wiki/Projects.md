How a git repository becomes a project brigade works on with `brigade project add`, what it discovers and guesses,
and how a project is listed, shown, paused and resumed.

## Commands

```
brigade project add <path> [--name N] [--acceptance CMD]... [--heavy CMD]... [--setup CMD]... [--force]
                           [--init-corpus] [--corpus-mode control|area] [--corpus FOLDER]
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

## A repository that already holds a corpus

A repository tracking a `.awawa` file is registered in one of two corpus modes, the `MODE` field of its `PROJECT`
entity, `control` when absent.

| `--corpus-mode` | How brigade uses the corpus |
|---|---|
| `control` | it writes its milestones and tasks in the corpus of the project, whose folder is the common path of the tracked `.awawa` files |
| `area` | it keeps to a folder of its own, `brigade/` at the root by default, holding its own schema and read as the awawa workspace: the corpus of the project is never read |

Without the option, `project add` asks on a terminal, then proposes the folder to confirm, `--corpus` overriding it;
with stdin not a terminal, it exits 2 naming `--corpus-mode`. `area` refuses a folder holding a corpus that is not
brigade's own, its schema differing from the template, and installs the template on a branch and pull request or merge
command, as `--init-corpus` does.

> **Watch out:** in `area` the schema of the folder declares `IMPL` a string, an awawa anchor resolving only inside its
> workspace, so the lint does not check the anchors: the promotion check at the preflight, which resolves each `IMPL`
> from the root of the repository, is their only check, and `project add` says so on stderr.

A project whose `MODE` is `none` is refused by every command that reads its corpus, exit 1 naming the mode, and the tick
skips it on stderr.

> **Watch out:** `brigade init` leaves a schema it finds in place: a machine installed before `MODE` keeps the old
> one, which refuses `area`, and `brigade doctor` reports that it differs from the shipped schema.

## A corpus for a project that has none

`brigade plan` and the tick read the awawa corpus of a project. `--init-corpus` gives one to a repository that tracks
no `.awawa` file: it commits the schema brigade reads as `_schema.awawa` of the folder `--corpus` names, `corpus/` by
default, on the branch `brigade/init-corpus` cut from the main branch, and registers the project with that folder. The
checkout of the project is left as it is.

| The forge of the project | What delivers the branch |
|---|---|
| `github` | a pull request into the main branch, whose number is printed |
| `none` | the branch stays local and the command prints `git -C <path> merge brigade/init-corpus` |

Once the branch is merged, `brigade plan context` and `brigade plan record` accept the project.

> **Watch out:** a repository already tracking a `.awawa` file exits 1 naming it, and so does a branch
> `brigade/init-corpus` that already exists.

<details><summary>How a write reaches the registry</summary>

Every write:

1. takes the lock of the corpus repository in `$XDG_STATE_HOME/brigade/locks/`;
2. runs `awawa fmt` on `projects.awawa` and `awawa lint --strict` on the corpus;
3. commits.

A failing lint restores the file and exits 1.

</details>
