brigade is a CLI, a timer and a local dashboard that run AI-agent waves unattended on one machine, across every
registered project. The CLI does everything mechanical; the agents only judge.

Each line below names a page and the question it answers: read the line, then the opening paragraph of the page, to
decide whether to read on. The pages are written in `wiki/` of the repository and published here on each push to
`main`.

## Getting started

- [Install](Install.md) — how to install brigade, check the machine with `brigade doctor` and create the operational
  corpus with `brigade init`.
- [Concepts](Concepts.md) — what each word of brigade means: project, request, wave, task, run, slot, role, tick,
  ledger, inbox, study and the others, each with the page that holds it.

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
- [Preflight](Preflight.md) — which deterministic checks run on the pull request of a task before any judgment.
- [Runs](Runs.md) — how a procedure runs as a slot, what a run keeps, and how it is held on the clock, stopped and
  pruned.
- [Verification](Verification.md) — how a review run judges the pull request of a task and records its verdict.
- [Review answers](Review-answers.md) — how a remediation run answers the findings of a review.
- [Rebase on the base](Rebase-on-the-base.md) — how a rebase run puts the branch of a task back on its base after a
  conflict.
- [Studies](Studies.md) — how a study collects, judges and outputs an answer, once or on a schedule.

## Observing

- [Inbox](Inbox.md) — what signals the inbox holds and how they are listed and dismissed.
- [Ledger](Ledger.md) — where every event is recorded and how `brigade ledger` summarises them.
- [Trails](Trails.md) — where the record of every subprocess is kept and how to read it.
- [Dashboard](Dashboard.md) — how `brigade serve` serves the local dashboard and which command each route runs.
- [Project tree at a ref](Project-tree-at-a-ref.md) — how to read a project's tree at a branch, a SHA or a worktree,
  and run awawa there.

## Contributing

- [Develop](Develop.md) — the local checks, what the continuous integration runs, the awawa recordings, and how this
  wiki is written and published.
- [Repository layout](Repository-layout.md) — where each part of brigade lives in its repository.
- [Command reference](Command-reference.md) — every command of brigade, what it does and the page that documents it.
