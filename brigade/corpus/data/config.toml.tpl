# brigade's machine configuration: read on this machine only, never committed.
# Every key is commented out, and brigade uses its own default for each.
# brigade keeps its state in $state_root and its caches in $cache_root.

# The client adapter that runs the agents: a built-in adapter, or an executable brigade-client-<name> on PATH.
# client = "claude-code"

# What fires the tick: systemd, cron or loop.
# scheduler = "systemd"

# The attempts at reading the token of a login of [forge_accounts], 1 or more, the delay doubling from one second;
# the attempts exhausted, the command stops and no other account is used in its place.
# forge_attempts = 3

# The form of the progress of a run: awawa, a corpus of STEP and HANDOVER entities, or markdown.
# document = "awawa"

# The root of an instructions corpus the roles are read from.
# instructions = ""

# The directory the tick cuts the worktree of each task under, absolute or relative to the repository of the project;
# by default .brigade/worktrees of the repository, which the tick adds to the .gitignore of the wave's branch.
# worktree_root = ""

# The link the dashboard opens a file with, {path} and {line} replaced.
# ide_link = ""

# The bound, in MB, of the cache of the trees brigade corpus extracts; the least recently read are removed past it.
# refs_cache_mb = 1024

# The seconds a run is given per step of its budget: the wall-time limit of a run is ceil(budget × 1.25) × seconds_per_step.
# seconds_per_step = 30

# The seconds before the wall-time limit of a segment at which a client that supports it stops between two steps,
# a positive number; a wall-time limit not above it gives no such stop.
# soft_limit_margin_s = 120

# The days a trail of ticks/ and commands/ is kept in $state_root, 1 or more; older trails are removed at each tick and command.
# trail_days = 7

# The finished and dead runs kept in $state_root/runs, 1 or more; past it, each run removes the oldest at its end,
# a running run and a run a resume after a rate limit takes up spared and not counted.
# runs_kept = 100

# The judging runs of studies the tick lets live at once on this machine, 1 or more; a scan launches no run and counts in
# no cap, and the tick never launches a study while a run of it is live.
# study_runs = 2

# The seconds between two reads of a running segment's output into the journal of its run, a positive number.
# journal_poll_s = 2

# The model and effort a reasoning level maps to, replacing that row of the client adapter's table;
# levels deepest, deep, standard, light.
# [reasoning.deep]
# model = ""
# effort = ""

# The settings of a client adapter, one table per adapter, each value a string the adapter reads;
# the fake adapter replays the recorded result documents of its recordings directory.
# [clients.fake]
# recordings = ""

# The role a slot runs, read from an AGENT entity of the instructions corpus, one key per slot bound;
# slots plan, build, review, remediate, rebase, report, triage, rules, explore.
# [slots]
# plan = ""

# The client adapter a slot runs on, in place of the CLIENT of the project and of the client key, one key per slot
# bound; slots plan, build, review, remediate, rebase, report, triage, rules, explore.
# [slot_clients]
# review = ""

# The gh login a slot acts as, or the key cli for the gh calls brigade makes itself: a process of a bound key
# carries the token gh auth token --user <login> prints, an unbound one acts as gh's active account;
# keys plan, build, review, remediate, rebase, report, triage, rules, explore and cli.
# [forge_accounts]
# cli = ""
