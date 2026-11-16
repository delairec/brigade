import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.document_shapes import SCHEMA_VERSION, TEXT
from brigade.system.validate_document import DocumentInvalid, Field, validate_document

KINDS = ("collect", "command", "gate", "judge", "output", "order", "corpus", "op")
OPS = ("worktree", "commit", "pull-request", "merge")
ON_FAIL_KEY = "on_fail"
PARK = "park"
ON_FAIL = re.compile(r"park|skip|stop|retry:[1-9][0-9]*")
PARAMETERS_KEY = "parameters"
PARAMETERS = Field(kinds=(dict,), optional=True)
STEP_SHAPE = Field(
    kinds=(dict,),
    fields={"kind": Field(kinds=(str,), values=KINDS), ON_FAIL_KEY: Field(kinds=(str,), optional=True)},
)
RECIPE_SHAPE = {
    "schema_version": SCHEMA_VERSION,
    "name": TEXT,
    "description": TEXT,
    "params": Field(kinds=(list,), items=TEXT),
    "max_wall": Field(kinds=(int,)),
    "steps": Field(kinds=(list,), items=STEP_SHAPE),
}
STEP_SHAPES = {
    "collect": {"collector": TEXT, PARAMETERS_KEY: PARAMETERS},
    "command": {"argv": Field(kinds=(list,), items=TEXT)},
    "gate": {"preflight": TEXT},
    "judge": {"slot": TEXT, "procedure": TEXT, "answer": TEXT},
    "output": {"output": TEXT},
    "order": {"recipe": TEXT, PARAMETERS_KEY: PARAMETERS},
    "corpus": {"entity": TEXT},
    "op": {"op": Field(kinds=(str,), values=OPS)},
}
FORBIDDEN_KEYS = ("client", "model")
PROJECT_PLACEHOLDERS = ("project",)
PLACEHOLDER = re.compile(r"\{([^{}]+)\}")
JUDGE_KIND = "judge"
VOWELS = tuple("aeiou")


@dataclass(frozen=True)
class RecipeResolvers:
    resolve_collector: Callable[[str], object]
    resolve_preflight: Callable[[str], object]
    resolve_output: Callable[[str], object]
    resolve_procedure: Callable[[str], object]
    slots: tuple[str, ...]
    client_binary: str | None


def _name_step(kind: str) -> str:
    article = "an" if kind.startswith(VOWELS) else "a"
    return f"{article} {kind} step"


def _check_keys(holder: dict, taken: tuple[str, ...], holder_name: str) -> None:
    for key in holder:
        if key not in (*taken, *FORBIDDEN_KEYS):
            raise DocumentInvalid(f"holds the key {key}, which {holder_name} does not take")


def _check_parameters(step: dict) -> None:
    parameters = step.get(PARAMETERS_KEY, {})
    try:
        validate_document(parameters, dict.fromkeys(parameters, TEXT))
    except DocumentInvalid as invalid:
        raise DocumentInvalid(f"{PARAMETERS_KEY}.{invalid}") from None


def _check_step(step: dict) -> None:
    shape = STEP_SHAPES[step["kind"]]
    _check_keys(step, (*STEP_SHAPE.fields, *shape), _name_step(step["kind"]))
    validate_document(step, shape)
    _check_parameters(step)
    on_fail = step.get(ON_FAIL_KEY, PARK)
    if not ON_FAIL.fullmatch(on_fail):
        raise DocumentInvalid(f"on_fail is {on_fail!r}, not park, skip, stop or retry:N")


def _check_schema(document: dict) -> None:
    validate_document(document, RECIPE_SHAPE)
    _check_keys(document, tuple(RECIPE_SHAPE), "a recipe")
    for index, step in enumerate(document["steps"]):
        try:
            _check_step(step)
        except DocumentInvalid as invalid:
            raise DocumentInvalid(f"steps[{index}]: {invalid}") from None


def _find_forbidden_keys(holder: dict, prefix: str) -> list[str]:
    return [
        f"{prefix}the key {key} names a client or a model, which a recipe never sets"
        for key in FORBIDDEN_KEYS
        if key in holder
    ]


def _resolve(resolve: Callable[[str], object], name: str, prefix: str) -> list[str]:
    try:
        resolve(name)
    except BrigadeError as error:
        return [f"{prefix}{error}"]
    return []


def _find_unresolved(step: dict, resolvers: RecipeResolvers, prefix: str) -> list[str]:
    resolved_names = {
        "collect": (("collector", resolvers.resolve_collector),),
        "gate": (("preflight", resolvers.resolve_preflight),),
        "output": (("output", resolvers.resolve_output),),
        JUDGE_KIND: (("procedure", resolvers.resolve_procedure),),
    }
    return [
        finding
        for key, resolve in resolved_names.get(step["kind"], ())
        for finding in _resolve(resolve, step[key], prefix)
    ]


def _find_unknown_slot(step: dict, slots: tuple[str, ...], prefix: str) -> list[str]:
    if step["kind"] != JUDGE_KIND or step["slot"] in slots:
        return []
    return [f"{prefix}no slot {step['slot']}: the slots are {', '.join(slots)}"]


def _find_client_binary(step: dict, client_binary: str | None, prefix: str) -> list[str]:
    if not any(Path(argument).name == client_binary for argument in step.get("argv", ())):
        return []
    return [f"{prefix}runs {client_binary}, the binary of the configured client"]


def _list_texts(value: str | dict | list) -> list[str]:
    if isinstance(value, str):
        return [value]
    items = value.values() if isinstance(value, dict) else value
    return [text for item in items for text in _list_texts(item)]


def _find_undeclared(step: dict, declared: tuple[str, ...], prefix: str) -> list[str]:
    return [
        f"{prefix}{{{name}}} names no param of the recipe"
        for text in _list_texts(step)
        for name in PLACEHOLDER.findall(text)
        if name not in declared
    ]


def _lint_step(step: dict, declared: tuple[str, ...], resolvers: RecipeResolvers, prefix: str) -> list[str]:
    return [
        *_find_forbidden_keys(step, prefix),
        *_find_unresolved(step, resolvers, prefix),
        *_find_unknown_slot(step, resolvers.slots, prefix),
        *_find_client_binary(step, resolvers.client_binary, prefix),
        *_find_undeclared(step, declared, prefix),
    ]


def lint_recipe(document: dict, resolvers: RecipeResolvers) -> list[str]:
    try:
        _check_schema(document)
    except DocumentInvalid as invalid:
        return [f"schema: {invalid}"]
    declared = (*document["params"], *PROJECT_PLACEHOLDERS)
    return [
        *_find_forbidden_keys(document, ""),
        *(
            finding
            for index, step in enumerate(document["steps"])
            for finding in _lint_step(step, declared, resolvers, f"steps[{index}]: ")
        ),
    ]
