from brigade.corpus.corpus_reader import CorpusReader
from brigade.corpus.describe_entity_card import describe_entity_card
from brigade.corpus.rank_naturally import rank_naturally
from brigade.corpus.select_view_cards import carries_search, describe_searched_texts

ERROR = "error"
WARNING = "warning"


def _describe_diagnostic(reader: CorpusReader, diagnostic: dict) -> dict:
    return {
        "rule": diagnostic["rule"],
        "severity": diagnostic["severity"],
        "file": reader.relative_file(diagnostic["file"]),
        "line": diagnostic["line"],
        "message": diagnostic["message"],
    }


def _locate_target(diagnostic: dict) -> str:
    entity = diagnostic["entity"]
    return "" if entity is None else f"@{entity['type']}.{entity['name']}"


def _rank_by_severity(diagnostics: list[dict]) -> tuple[int, int]:
    severities = [diagnostic["severity"] for diagnostic in diagnostics]
    return -severities.count(ERROR), -severities.count(WARNING)


def _searched_diagnostics(diagnostics: list[dict]) -> list[str]:
    return [text for diagnostic in diagnostics for text in (diagnostic["rule"], diagnostic["message"])]


def describe_health_view(reader: CorpusReader, search: str | None) -> dict:
    by_entity: dict[str, list[dict]] = {}
    by_file: dict[str, list[dict]] = {}
    for diagnostic in reader.lint()["diagnostics"]:
        described = _describe_diagnostic(reader, diagnostic)
        target = _locate_target(diagnostic)
        if reader.row(target) is not None:
            by_entity.setdefault(target, []).append(described)
        else:
            by_file.setdefault(described["file"], []).append(described)
    entities = [
        {
            "entity": describe_entity_card(reader, reader.row(target)),
            "diagnostics": sorted(diagnostics, key=lambda diagnostic: diagnostic["line"]),
        }
        for target, diagnostics in by_entity.items()
    ]
    files = [
        {"file": file, "diagnostics": sorted(diagnostics, key=lambda diagnostic: diagnostic["line"])}
        for file, diagnostics in by_file.items()
    ]
    counts = reader.status
    return {
        "errors": counts["diagnostics"]["errors"],
        "warnings": counts["diagnostics"]["warnings"],
        "unresolved": counts["references"]["unresolved"],
        "entities": sorted(
            (
                ailing
                for ailing in entities
                if carries_search(
                    [*describe_searched_texts(ailing["entity"]), *_searched_diagnostics(ailing["diagnostics"])],
                    search,
                )
            ),
            key=lambda ailing: (_rank_by_severity(ailing["diagnostics"]), rank_naturally(ailing["entity"]["code"])),
        ),
        "files": sorted(
            (
                ailing
                for ailing in files
                if carries_search([ailing["file"], *_searched_diagnostics(ailing["diagnostics"])], search)
            ),
            key=lambda ailing: (_rank_by_severity(ailing["diagnostics"]), rank_naturally(ailing["file"])),
        ),
    }
