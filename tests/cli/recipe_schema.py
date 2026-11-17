RECIPE_SCHEMA = (
    "\n"
    "SCHEMA RECIPE\n"
    '\tDESC "a kind of work brigade runs as ordered steps; its name is the name of the recipe"\n'
    "\tFIELD SCHEMA_VERSION uint\n\t\tREQUIRED\n"
    "\tFIELD MAX_WALL uint\n\t\tREQUIRED\n"
    "\tFIELD STEP command\n\t\tREQUIRED\n\t\tREPEATABLE\n"
    "\t\tFIELD ARGV string\n\t\t\tREPEATABLE\n"
)
