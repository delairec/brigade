LEDGER_SCHEMA_VERSION = 1
ENVELOPE_KEYS = ("schema_version", "ts", "event")
RUN_FINISHED = "run.finished"
EVENT_FIELDS = {
    RUN_FINISHED: ("wave", "task", "procedure", "role", "slot", "segment", "outcome", "error_class", "steps"),
    "wave.started": ("wave", "project"),
    "wave.paused": ("wave",),
    "wave.resumed": ("wave",),
    "task.parked": ("wave", "task"),
    "pr.merged": ("project", "wave", "task", "pr", "rounds"),
    "order.done": ("project", "kind"),
    "signal.recorded": ("project",),
    "pattern.ratified": ("project",),
    "constraint.delivered": ("project",),
}
