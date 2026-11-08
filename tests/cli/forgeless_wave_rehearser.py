from tests.cli.wave_rehearser import AWAIT_THE_RELEASE, READ_THE_BRIEF, WaveRehearser

MILESTONE_BRANCH = "integration/empty-cart"
ONE_TASK_PLAN = (
    'MILESTONE M1\n\tTITLE "Empty cart"\n\tSTATUS active\n\n'
    'TASK S1\n\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tTYPE feat\n\tMILESTONE @MILESTONE.M1\n'
)
FORGELESS_BUILDER_PLAY = (
    READ_THE_BRIEF + AWAIT_THE_RELEASE + 'task=$(read_argument task | sed "s/^@TASK\\.//")\n'
    'printf \'%s\\n\' "$task" > "delivered-$task.txt"\n'
    "grep -rl 'STATUS todo' corpus | xargs sed -i 's/STATUS todo/STATUS implemented/'\n"
    'git add -- "delivered-$task.txt" corpus && git commit --quiet -m "feat: deliver $task" >&2\n'
    "brigade task check >&2\n"
    'cat -- "$1"\n'
)
FORGELESS_REVIEWER_PLAY = (
    READ_THE_BRIEF + AWAIT_THE_RELEASE + 'verdict="$BRIGADE_RUN_DIR/verdict.json"\n'
    'printf \'{"head": "%s", "verdict": "pass", "findings": []}\\n\' "$(git rev-parse HEAD)" > "$verdict"\n'
    'brigade verify verdict --file "$verdict" >&2\n'
    'cat -- "$1"\n'
)


class ForgelessWaveRehearser(WaveRehearser):
    def prepare_sandbox(self, path):
        super().prepare_sandbox(path)
        self.project.run_git("remote", "remove", "origin")

    def prepare_client(self, recordings, plays):
        super().prepare_client(recordings, plays)
        (plays / "planner").write_text((plays / "planner").read_text().replace(self._read_plan(plays), ONE_TASK_PLAN))
        (plays / "builder").write_text(FORGELESS_BUILDER_PLAY)
        (plays / "reviewer").write_text(FORGELESS_REVIEWER_PLAY)

    @staticmethod
    def _read_plan(plays) -> str:
        return (plays / "planner").read_text().split("<<'PLAN'\n", 1)[1].split("PLAN\n", 1)[0]

    def register_sandbox(self):
        self.run_brigade("project", "add", str(self.project.path), "--acceptance", "true")

    def is_milestone_reported(self) -> bool:
        events = self.read_events()
        merged = [event for event in events if event["event"] == "task.state" and event["state"] == "merged"]
        reported = [event for event in events if event["event"] == "milestone.reported"]
        return len(merged) == 1 and bool(reported)

    def list_event_names(self) -> list[str]:
        return [event["event"] for event in self.read_events()]

    def find_event(self, name: str) -> dict:
        [event] = [event for event in self.read_events() if event["event"] == name]
        return event
