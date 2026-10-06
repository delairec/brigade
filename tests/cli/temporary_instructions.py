from pathlib import Path

SCHEMA = (
    "SCHEMA AGENT\n"
    '\tDESC "a role"\n'
    "\tFIELD WORK string\n\t\tREQUIRED\n\t\tREPEATABLE\n"
    "\tFIELD REASONING deepest|deep|standard|light\n\t\tREQUIRED\n"
    "\tFIELD CAPABILITY read|write|shell|net\n\t\tREQUIRED\n\t\tREPEATABLE\n"
    "\tFIELD BUDGET uint\n"
    "\tFIELD RETURNS string\n\t\tREQUIRED\n\t\tREPEATABLE\n"
    "\tFIELD LOADS @RULE\n\t\tREPEATABLE\n"
    "\n"
    "SCHEMA RULE\n"
    '\tDESC "a rule"\n'
    "\tFIELD SPEC string\n\t\tREQUIRED\n"
)
PLANNER = (
    "AGENT planner\n"
    '\tWORK "the plan of a wave"\n'
    '\tWORK "the order of its tasks"\n'
    "\tREASONING deep\n"
    "\tCAPABILITY read\n"
    "\tCAPABILITY shell\n"
    "\tBUDGET 40\n"
    '\tRETURNS "the wave plan"\n'
    '\tRETURNS "the blockers"\n'
    "\tLOADS @RULE.plans_are_short\n"
    "\n"
    "AGENT stray\n"
    '\tWORK "anything"\n'
    "\tREASONING light\n"
    "\tCAPABILITY read\n"
    "\tBUDGET 10\n"
    '\tRETURNS "something"\n'
    "\n"
    "RULE plans_are_short\n"
    '\tSPEC "a plan fits one screen"\n'
)


class TemporaryInstructions:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True)
        (root / "_schema.awawa").write_text(SCHEMA)
        self.write_agents(PLANNER)

    def write_agents(self, content: str) -> None:
        (self.root / "agents.awawa").write_text(content)
