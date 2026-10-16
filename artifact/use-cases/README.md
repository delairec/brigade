# Use-case map

The sources of the published Artifact "Brigade cas d'utilisation",
<https://claude.ai/artifact/KCyasde1gfUbiMcHYqgSe4>: one sequence diagram per use case of brigade, from the operator's intent
to the code that answers it, then the holes and defects found on the way and the critical path to the night delivery.

- `index.html` — the page; it fetches the files of `data/` and draws every diagram from them.
- `data/usecases-A.json`, `usecases-B.json`, `usecases-C.json` — the use cases and issues of the three families.
- `data/cross.json` — the cross-cutting pass: verdicts on the issues, duplicates, new issues, critical path.
- `data/milestones.json` — the task counts by milestone and status; `data/meta.json` — the line under the title.
- `briefs/` — the briefs of the runs that produce the data.

## Redoing the map

1. Launch the three inventory runs of `briefs/inventory.md` in one message, then the pass of `briefs/cross.md`.
2. Count the tasks of each milestone with `awawa status TASK --where MILESTONE==@MILESTONE.X --json .` into
   `data/milestones.json`, and set the commit and the date in `data/meta.json`.
3. Copy the four files the runs wrote into `data/`, view the page served locally (`python3 -m http.server` from this
   folder), and republish it with the Artifact tool, `url` set to the address above after a read of it, the files
   of `data/` passed as `files` under the same paths.
