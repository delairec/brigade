# brigade

A CLI, a timer and a local dashboard that run AI-agent waves unattended on one machine, across every
registered project. The CLI does everything mechanical; the agents only judge.

This repository holds the plan before any code:

- `artifact/` — the sources of the published Artifact "Brigade Blueprint" (overview, plan, mockups, task board,
  demo, brief); `index.html` is the page, `parts/` the fragments it fetches.
- `corpus/` — the project's own awawa corpus: the schema, the milestones, the POC tasks (all `draft` until the first
  wave ratifies them), the decisions of the plan. Read it with `awawa status .` from this directory.
- `schema/_schema.awawa.tpl` — the schema of the operational corpus `brigade init` installs in the config directory
  (kept as a template so it does not join this corpus).
- `HANDOFF.md` — the working notes of the planning run: what was asked, what was answered, what was decided, what remains.

The status of a POC task is its `STATUS` in `corpus/tasks.awawa`, and nowhere else; the task board of the Artifact
is a view of it (@DECISION.TheCorpusIsTheHomeOfTaskStatusTheBoardItsView), refreshed by the command B41 delivers.
Until then the board's statuses are stale and bind nothing.
