from brigade.runs.describe_progress import describe_progress
from brigade.runs.plan_run import RunPlan
from brigade.runtime import Runtime
from brigade.system.ask_document import DocumentQuestion, ask_document


def ask_progress(plan: RunPlan, operation: str, runtime: Runtime) -> dict:
    question = DocumentQuestion(
        document_name=plan.configuration.document, operation=operation, request=describe_progress(plan)
    )
    return ask_document(plan.document, question, runtime)
