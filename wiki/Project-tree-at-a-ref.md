How to read a registered project's tree at a branch, a SHA or a worktree with `brigade corpus`, run awawa there, list
its entities, print one view of its corpus, and how the cache of extracted trees is bounded.

## Commands

```
brigade corpus <project> [--json] [-- <awawa args>]
brigade corpus <project> --ref <branch|sha> [--json] [-- <awawa args>]
brigade corpus <project> --ref worktree:<branch> [--json] [-- <awawa args>]
brigade corpus <project> --worktree <path> [--json] [-- <awawa args>]
brigade corpus <project> [--ref <ref>] --type <TYPE> [--field <FIELD>] [--entity @TYPE.Name] [--json]
brigade corpus <project> [--ref <ref>] --view tree|board|dependencies|health [--type <TYPE>] [--field <FIELD>]
               [--filter <field>=<value> ...] [--search <text>] [--entity @TYPE.Name] [--json]
```

| Option | Reads |
|---|---|
| neither `--ref` nor `--worktree` | the branch of the project's `MAIN` field, as `--ref <that branch>` would; the ref of the document names that branch |
| `--ref <branch\|sha>` | `git archive` of that commit, the whole tree, extracted once into `$XDG_CACHE_HOME/brigade/refs/<project>/<sha>/` |
| `--ref worktree:<branch>` | in place, the worktree where that branch is checked out; uncommitted edits are visible |
| `--worktree <path>` | in place, the worktree at that path, a detached HEAD included; uncommitted edits are visible |

The command prints the project, the ref, the SHA, the kind (`archive` or `worktree`) and the root of the tree, as text
or, with `--json`, a JSON document that also carries `types`, the entity types of the corpus at the ref read, with or
without `--type`.

## Running awawa on the tree

Given `-- <awawa args>`, it runs awawa with those arguments at the root of the tree instead, and passes its stdout,
its stderr and its exit code through unchanged, after one stderr line naming the SHA it read.

```
brigade corpus <project> --ref main -- status .
```

## Listing entities

| Option | Adds to the document |
|---|---|
| `--type <TYPE>` | the entities of that type with their status, their file and their line |
| `--field <FIELD>` | the board: the entities grouped by the values of that field, those without it in a column of their own |
| `--entity @TYPE.Name` | what that entity reaches and what references it |

> **Watch out:** `--field` or `--entity` without `--type` exits 1.

## Views of the corpus

`--view` prints the document of one view of the corpus, by the rules of the IntelliJ plugin awawa-ui, beside `project`,
`ref`, `sha`, `kind`, `root`, `types` and `awawa_web`; as text, the same document indented. Without `--view` the
command prints what the sections above describe.

| `--view` | The document holds |
|---|---|
| `tree` | `domain`, the types using the most statuses first, and `schema`, `SCHEMA`, `FIELDSET` and `SHAPE` apart; a type whose entities stand at a status for at least half of them holds `groups`, one per status in the order of its lifecycle, `null` for the entities at no status, the last value of the lifecycle `collapsed`; any other type holds its `entities` |
| `board` | with `--type`, `field`, `STATUS` unless `--field` names another, and `columns`: for a field of literals one per value the schema admits, in schema order; for any other field one per each of its 5 most frequent values, then `Others (k)`, whose entities carry their `value`; `(none)` last for the entities leaving the field empty |
| `dependencies` | with `--type`, `field`, the first field referring to entities of the type unless `--field` names one, and `roots`, the entities waiting on nothing, each with its `dependents`; `in_cycle` flags an entity in a cycle, `already_above` one met again along its own path, which goes no deeper; a cycle no root reaches gets a root of its own |
| `health` | `errors`, `warnings` and `unresolved` as `awawa status` counts them, `entities`, the diagnostics of `awawa lint` gathered per entity, the most errors first, and `files`, the diagnostics on no entity under their file |

Each entity of a view carries its `type`, its `target`, its `code`, the name as written, its `label`, the first
required, single-valued string field of its type, else its name read as a sentence, up to four `facts`, the fields it
fills whose values are literals, numbers, identifiers, references or shapes, a reference carrying the `status` of its
target, its `status` and its `position` in the lifecycle of its type, `waiting` when it refers to an entity of its own
type standing no further along that lifecycle, its `file`, its `line` and its `ide_link`.

| Option | With `--view` |
|---|---|
| `--filter <field>=<value>` | keeps the entities of `--type` whose field holds one of the values given for it, repeatable; `<field>.<field>=<value>` reads one field of the entities a reference field refers to, one level deep; an entity whose prerequisites are all filtered out becomes a root; the health view leaves the filters aside |
| `--search <text>` | keeps the entities whose label, code, facts, status or file carries the text, case aside, and in the health view the diagnostics whose rule or message carries it |
| `--entity @TYPE.Name` | adds `detail`: the entity as `awawa show --json` answers it, `references`, the entities it refers to, and `referenced_by`, those that refer to it, each with its code, its label and its status |

> **Watch out:** `--view board` or `--view dependencies` without `--type` exits 1, and so does a type with no field
> referring to its own entities under `--view dependencies` without `--field`.

The command reads the corpus through awawa alone: one `awawa status --json`, one `awawa context --depth 0
--with-schema --json` per type shown, one `awawa show --json` per entity, eight at a time, and `awawa lint --json` for
the health view.

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
