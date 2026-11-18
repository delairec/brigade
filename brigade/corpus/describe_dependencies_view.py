from brigade.corpus.corpus_reader import CorpusReader


def _reach(prerequisites: dict[str, list[str]], start: str) -> set[str]:
    reached: set[str] = set()
    pending = list(prerequisites[start])
    while pending:
        target = pending.pop()
        if target not in reached:
            reached.add(target)
            pending.extend(prerequisites[target])
    return reached


def _describe_node(card: dict, dependents: dict[str, list[dict]], cyclic: set[str], above: frozenset[str]) -> dict:
    target = card["target"]
    already_above = target in above
    return card | {
        "in_cycle": target in cyclic,
        "already_above": already_above,
        "dependents": []
        if already_above
        else [_describe_node(other, dependents, cyclic, above | {target}) for other in dependents[target]],
    }


def describe_dependencies_view(reader: CorpusReader, cards: list[dict], field: str) -> dict:
    targets = {card["target"] for card in cards}
    prerequisites = {
        card["target"]: list(
            dict.fromkeys(
                atom
                for atoms in reader.values(reader.row(card["target"])).get(field, [])
                for atom in atoms
                if atom in targets
            )
        )
        for card in cards
    }
    dependents = {card["target"]: [] for card in cards}
    for card in cards:
        for prerequisite in prerequisites[card["target"]]:
            dependents[prerequisite].append(card)
    reaches = {target: _reach(prerequisites, target) for target in targets}
    cyclic = {target for target in targets if target in reaches[target]}
    roots = [card for card in cards if not prerequisites[card["target"]]]
    reached = {root["target"] for root in roots} | {
        target for target in targets if any(root["target"] in reaches[target] for root in roots)
    }
    for card in cards:
        target = card["target"]
        component = {target} | {other for other in reaches[target] if target in reaches[other]}
        is_source = all(set(prerequisites[member]) <= component for member in component)
        if is_source and not component & reached:
            roots.append(card)
            reached |= component
    nodes = [_describe_node(root, dependents, cyclic, frozenset()) for root in roots]
    return {"field": field, "roots": nodes}
