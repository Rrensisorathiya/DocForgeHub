from fastapi import APIRouter
from schemas.document_schema import QuestionnaireCreateRequest
from services.questionnaire_repository import (
    create_questionnaire,
    list_questionnaires,
    get_questionnaire,
    delete_questionnaire,
)

router = APIRouter()


@router.post("/", summary="Create a new questionnaire")
def create(payload: QuestionnaireCreateRequest):
    """
    Create a questionnaire for a specific document type.

    The questionnaire defines what questions users must answer before generating a document.
    """
    return create_questionnaire(payload.dict())


@router.get("/", summary="List all questionnaires")
def list_all():
    return list_questionnaires()


@router.get("/{q_id}", summary="Get a questionnaire by ID")
def get_one(q_id: str):
    return get_questionnaire(q_id)


@router.delete("/{q_id}", summary="Delete a questionnaire by ID")
def delete_one(q_id: str):
    return delete_questionnaire(q_id)
# from fastapi import APIRouter
# from services.questionnaire_repository import (
#     create_questionnaire,
#     list_questionnaires,
#     get_questionnaire,
#     delete_questionnaire,
# )

# router = APIRouter()

# @router.post("/")
# def create(payload: dict):
#     return create_questionnaire(payload)

# @router.get("/")
# def list_all():
#     return list_questionnaires()

# @router.get("/{q_id}")
# def get_one(q_id: str):
#     return get_questionnaire(q_id)

# @router.delete("/{q_id}")
# def delete_one(q_id: str):
#     return delete_questionnaire(q_id)
