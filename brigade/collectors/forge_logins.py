from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.registry.read_project_forge import NO_FORGE
from brigade.runtime import Runtime
from brigade.system.ask_login_environment import ask_login_environment

NAME = "forge-logins"
FRESH_AT_EACH_CALL = False
NO_ITEMS = []
NO_LOGINS = []


def _group_keys_by_login(forge_accounts: dict) -> dict:
    keys_by_login = {}
    for key, login in forge_accounts.items():
        keys_by_login.setdefault(login, []).append(key)
    return keys_by_login


def _describe_logins(equipment: CollectorEquipment, runtime: Runtime) -> list[dict]:
    return [
        {
            "login": login,
            "keys": keys,
            "token": ask_login_environment(equipment.forge, equipment.forge_name, login, runtime) is not None,
        }
        for login, keys in _group_keys_by_login(equipment.configuration.forge_accounts).items()
    ]


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    logins = NO_LOGINS if equipment.forge_name == NO_FORGE else _describe_logins(equipment, runtime)
    return {**describe_collection(NAME, runtime, {"logins": logins}, NO_ITEMS), "cache": FRESH_AT_EACH_CALL}
