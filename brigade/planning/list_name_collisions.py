from brigade.planning.read_entity_sites import EntitySite
from brigade.planning.read_plan import PlanEntity


def list_name_collisions(sites: tuple[EntitySite, ...], plan: tuple[PlanEntity, ...]) -> list[str]:
    places = {(site.type, site.name): f"{site.file}:{site.line}" for site in sites}
    return [
        f"@{plan_entity.type}.{plan_entity.entity.name} already exists at {places[plan_entity.type, plan_entity.entity.name]}"
        for plan_entity in plan
        if (plan_entity.type, plan_entity.entity.name) in places
    ]
