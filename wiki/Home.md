brigade is a CLI, a timer and a local dashboard that run AI-agent waves unattended on one machine, across every
registered project. The CLI does everything mechanical; the agents only judge.

Each line below names a page and the question it answers: read the line, then the opening paragraph of the page, to
decide whether to read on. The pages are written in `wiki/` of the repository and published here on each push to
`main`.

## Getting started

- [Install](Install.md) — how to install brigade, check the machine with `brigade doctor` and create the registry with
  `brigade init`.
- [Platforms](Platforms.md) — which platforms brigade runs on, feature by feature, and why a feature breaks where it
  does.
- [Glossary](Glossary.md) — the page to read when a word is unknown: what each word of brigade means, every command,
  entity and field among them, each with the page that holds it and the task that delivers it.

## Configuring

- [Projects](Projects.md) — how a git repository is registered as a project, and paused or resumed.
- [Client adapters](Client-adapters.md) — which AI clients brigade runs its agents through, what each can do, and the
  fallbacks for what it cannot.
- [Roles](Roles.md) — what a slot and a role are, and where a slot finds its role.
- [Tick and scheduler](Tick-and-scheduler.md) — what a tick does with the facts, and how the scheduler fires it every
  five minutes.

## Running work

- [Waves](Waves.md) — how a request is planned and how a wave of ratified tasks is started, followed, cancelled and
  resumed.
- [Tasks](Tasks.md) — what a build run does from the worktree of its task: context, checks, pull request, promotion.
- [Preflight](Preflight.md) — where a preflight resolves from, how a project adds a custom one with `brigade preflight add`, and which deterministic checks run on the pull request of a task before any judgment.
- [Runs](Runs.md) — how a procedure runs as a slot, what a run keeps, and how it is held on the clock, stopped and
  pruned.
- [Review](Review.md) — how a review run judges the pull request of a task and records its verdict.
- [Review answers](Review-answers.md) — how a remediation run answers the findings of a review.
- [Rebase on the base](Rebase-on-the-base.md) — how a rebase run puts the branch of a task back on its base after a
  conflict.
- [Studies](Studies.md) — how a study collects, judges and outputs an answer, once or on a schedule.
- [Recipes](Recipes.md) — how to write a recipe from the example `pr-usage-report`: its params, its steps, its gate,
  its judge and its output.

## Observing

- [Inbox](Inbox.md) — what signals the inbox holds, how they are listed and dismissed, and how a pattern is ratified.
- [Ledger](Ledger.md) — where every event is recorded and how `brigade ledger` summarises them.
- [Trails](Trails.md) — where the record of every subprocess is kept and how to read it.
- [Dashboard](Dashboard.md) — how `brigade serve` serves the local dashboard and which command each route runs.
- [Project tree at a ref](Project-tree-at-a-ref.md) — how to read a project's tree at a branch, a SHA or a worktree,
  and run awawa there.
- [Proof of M6](Proof-of-M6.md) — whether brigade delivers unattended and costs fewer turns than agents launched by
  hand: the closed waves of 2026-11-18 to 2026-11-19 against the baseline of 2026-10-03.

## Contributing

- [Develop](Develop.md) — the local checks, what the continuous integration runs, the awawa recordings, and how this
  wiki is written and published.
- [Repository layout](Repository-layout.md) — where each part of brigade lives in its repository.
- [Command reference](Command-reference.md) — every command of brigade, what it does and the page that documents it.
