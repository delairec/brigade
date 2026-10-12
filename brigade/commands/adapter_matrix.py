from brigade.command import Argument, Command
from brigade.errors import BrigadeError, UsageError
from brigade.runtime import Runtime
from brigade.system.ask_named_client import ask_named_client
from brigade.system.client_question import ClientQuestion
from brigade.system.list_client_adapters import SUPPORTED_CLIENT, ClientAdapter, list_client_adapters
from brigade.system.probe_answer import ProbeAnswer
from brigade.system.probe_request import ProbeRequest
from brigade.system.read_configuration import Configuration
from brigade.system.read_optional_configuration import read_optional_configuration

SCHEMA_VERSION = 1
OPERATION_CAPABILITIES = ("launch", "result", "resume", "transcripts", "actions")
FEATURE_CAPABILITIES = ("step_count", "tool_grants", "reset_hour", "graceful_stop")
CAPABILITIES = OPERATION_CAPABILITIES + FEATURE_CAPABILITIES
FALLBACKS = {
    "resume": "a fresh launch from the progress file",
    "transcripts": "brigade's journal of the run",
    "actions": "one raw record per line of the client's output",
    "step_count": "steps null and the run held on the clock alone",
    "tool_grants": "the client's unattended mode and a disposable worktree for a reading slot",
    "reset_hour": "now plus thirty minutes",
    "graceful_stop": "the hard cut at the wall-time limit",
}
FULL = "full"
FALLBACK = "fallback"
ABSENT = "absent"
NO_ERROR = None
NO_CAPABILITIES = None
WORD_SEPARATOR = "_"
LABEL_SEPARATOR = " "
COLUMN_GAP = 2
LEGEND_TITLE = "fallbacks"
LEGEND_INDENT = "  "
ERROR_PREFIX = "error: "
HEADER = ("adapter", "audience", *(capability.replace(WORD_SEPARATOR, LABEL_SEPARATOR) for capability in CAPABILITIES))
AUDIENCE_TITLES = {"supported_client": "Supported client", "test_suite": "Test-suite adapter"}
FALLBACKS_TITLE = "Fallbacks:"
CELL_SEPARATOR = "|"
ESCAPED_CELL_SEPARATOR = "\\|"
HEADER_RULE = "---"
EMPTY_CELL = ""


def _grade(capability: str, declared: tuple[str, ...]) -> str:
    if capability in declared:
        return FULL
    if capability in FALLBACKS:
        return FALLBACK
    return ABSENT


def _grade_capabilities(probe: ProbeAnswer) -> dict:
    return {
        **{capability: _grade(capability, probe.operations) for capability in OPERATION_CAPABILITIES},
        **{capability: _grade(capability, probe.features) for capability in FEATURE_CAPABILITIES},
    }


def _describe_adapter(runtime: Runtime, configuration: Configuration, adapter: ClientAdapter) -> dict:
    row = {"name": adapter.name, "audience": adapter.audience}
    try:
        client = runtime.resolve_plugin("client", adapter.name)
        probe = ask_named_client(client, ClientQuestion(adapter.name, ProbeRequest()), configuration, runtime)
    except BrigadeError as error:
        return {**row, "capabilities": NO_CAPABILITIES, "error": str(error)}
    return {**row, "capabilities": _grade_capabilities(probe), "error": NO_ERROR}


def _order_row(row: dict) -> tuple[bool, str]:
    return row["audience"] != SUPPORTED_CLIENT, row["name"]


def _label(key: str) -> str:
    return key.replace(WORD_SEPARATOR, LABEL_SEPARATOR)


def _list_cells(row: dict) -> tuple[str, ...]:
    return (row["name"], _label(row["audience"]), *(row["capabilities"][capability] for capability in CAPABILITIES))


def _list_measured_cells(row: dict) -> tuple[str, ...]:
    if row["error"] is not None:
        return row["name"], _label(row["audience"])
    return _list_cells(row)


def _measure_columns(adapters: list[dict]) -> list[int]:
    rows = [HEADER, *(_list_measured_cells(row) for row in adapters)]
    return [max(len(cells[column]) for cells in rows if column < len(cells)) for column in range(len(HEADER))]


def _join_cells(cells: tuple[str, ...], widths: list[int]) -> str:
    padded = [f"{cell:<{width + COLUMN_GAP}}" for cell, width in zip(cells[:-1], widths, strict=False)]
    return "".join([*padded, cells[-1]])


def _render_row(row: dict, widths: list[int]) -> str:
    if row["error"] is not None:
        return _join_cells((row["name"], _label(row["audience"]), f"{ERROR_PREFIX}{row['error']}"), widths)
    return _join_cells(_list_cells(row), widths)


def _render_legend(fallbacks: dict) -> list[str]:
    labels = {capability: f"no {_label(capability)}" for capability in fallbacks}
    width = max(len(label) for label in labels.values())
    return [
        LEGEND_TITLE,
        *(f"{LEGEND_INDENT}{labels[capability]:<{width + COLUMN_GAP}}{text}" for capability, text in fallbacks.items()),
    ]


def _render_text(document: dict) -> str:
    widths = _measure_columns(document["adapters"])
    table = [_join_cells(HEADER, widths), *(_render_row(row, widths) for row in document["adapters"])]
    return "\n".join([*table, "", *_render_legend(document["fallbacks"])])


def _join_markdown_cells(cells: list[str]) -> str:
    return f"| {' | '.join(cells)} |"


def _list_markdown_cells(row: dict) -> list[str]:
    if row["error"] is not None:
        message = row["error"].replace(CELL_SEPARATOR, ESCAPED_CELL_SEPARATOR)
        return [row["name"], f"{ERROR_PREFIX}{message}", *([EMPTY_CELL] * (len(CAPABILITIES) - 1))]
    return [row["name"], *(row["capabilities"][capability] for capability in CAPABILITIES)]


def _render_table(audience: str, adapters: list[dict]) -> str:
    header = [AUDIENCE_TITLES[audience], *(_label(capability).capitalize() for capability in CAPABILITIES)]
    rows = [_list_markdown_cells(row) for row in adapters if row["audience"] == audience]
    return "\n".join(_join_markdown_cells(cells) for cells in [header, [HEADER_RULE] * len(header), *rows])


def _render_markdown(document: dict) -> str:
    tables = [_render_table(audience, document["adapters"]) for audience in AUDIENCE_TITLES]
    legend = "\n".join(f"- no {_label(capability)}: {text}" for capability, text in document["fallbacks"].items())
    return "\n\n".join([*tables, FALLBACKS_TITLE, legend])


def _read_request(options):
    if options.markdown and options.json:
        raise UsageError("--markdown and --json exclude each other")
    return options


def _decide_exit_code(document: dict) -> int:
    if any(row["error"] is not None for row in document["adapters"]):
        return 1
    return 0


def adapter_matrix(request, runtime: Runtime) -> dict:
    configuration = read_optional_configuration(runtime.paths.configuration_file)
    rows = [_describe_adapter(runtime, configuration, adapter) for adapter in list_client_adapters(runtime)]
    return {"schema_version": SCHEMA_VERSION, "adapters": sorted(rows, key=_order_row), "fallbacks": FALLBACKS}


COMMAND = Command(
    path=("adapter", "matrix"),
    help="print the capabilities every client adapter declares",
    group_help="answer one operation of the configured client adapter, or print the matrix of every adapter",
    arguments=(Argument(("--markdown",), {"action": "store_true", "help": "print the matrix as Markdown tables"}),),
    run=adapter_matrix,
    read_request=_read_request,
    render_text=_render_text,
    render_markdown=_render_markdown,
    decide_exit_code=_decide_exit_code,
)
