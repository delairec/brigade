from brigade.studies.locate_study_project import StudyProject
from brigade.studies.study_run_context import StudyRunContext
from brigade.system.parse_configuration import CLI_KEY
from brigade.system.read_account_environment import ForgeAccount, read_account_environment

UNBOUND_ENVIRONMENT = {}


def read_publication_environment(context: StudyRunContext, project: StudyProject) -> dict:
    if project.forge is None:
        return UNBOUND_ENVIRONMENT
    account = ForgeAccount(forge=context.equipment.resolve_forge(project.forge), forge_name=project.forge, key=CLI_KEY)
    return read_account_environment(account, context.equipment.collector_equipment.configuration, context.runtime)
