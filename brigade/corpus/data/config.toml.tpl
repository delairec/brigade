# brigade's machine configuration: read on this machine only, never committed.
# Every key is commented out, and brigade uses its own default for each.
# brigade keeps its state in $state_root and its caches in $cache_root.

# The client adapter that runs the agents: a built-in adapter, or an executable brigade-client-<name> on PATH.
# client = "claude-code"

# What fires the tick: systemd, cron or loop.
# scheduler = "systemd"

# The GitHub account gh acts as for brigade's writes.
# forge_account = ""

# The root of an instructions corpus the roles are read from.
# instructions = ""

# The link the dashboard opens a file with, {path} and {line} replaced.
# ide_link = ""

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
# slots plan, build, verify, review, rebase, report, triage, rules, explore.
# [slots]
# plan = ""
