What a slot and a role are, where a slot finds its role, and how `brigade roles` lists, shows and lints them.

## Commands

```
brigade roles list [--json]                  # the slot, the role, its source and the model of each slot
brigade roles show <slot> [--json]           # the role file the slot resolves to
brigade roles show <slot> --short [--json]   # its front matter and the size of its body, in lines and bytes
brigade roles lint [--json]                  # the built-in and the machine role files; exit 1 on a finding
```

## Slots

A procedure calls a slot, never a role. There are nine slots: `plan`, `build`, `review`, `remediate`, `rebase`,
`report`, `triage`, `rules` and `explore`.

A slot resolves to the first of:

1. the file of `$XDG_CONFIG_HOME/brigade/roles/` whose front matter declares that slot;
2. the AGENT entity of the instructions corpus (the `instructions` key of `config.toml`) that the table `[slots]`
   binds to it, `plan = "<agent name>"`, read through awawa at each resolution: its fields fill the front matter
   and its `awawa context` package is the body;
3. brigade's built-in role, under `brigade/roles/data/`.

A project can bind its slots otherwise with `ROLE` and `ROLESET`, as [Runs](Runs.md) says.

## Role files

A role is a Markdown file: a front matter between two `---` lines, then the system prompt. The front matter declares:

| Key | Values |
|---|---|
| `name`, `slot`, `work` | |
| `reasoning` | `deepest`, `deep`, `standard`, `light` |
| `capabilities` | `read`, `write`, `shell`, `net`, comma-separated |
| `budget`, `returns` | |

A role never names a model: the client adapter binds one to its reasoning level.
