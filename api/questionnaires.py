from fastapi import APIRouter, Query
from typing import Optional
from services.questionnaire_repository import list_questionnaires, get_questionnaire, get_questionnaire_by_type

router = APIRouter()


@router.get("/", summary="List all questionnaires (seeded from Question_Answer.json)")
def list_all(
    department: Optional[str] = Query(None, description="Filter by department"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
):
    return list_questionnaires(department=department, document_type=document_type)


@router.get("/by-type", summary="Get questionnaire by department and document type")
def get_by_type(
    department: str = Query(..., description="Department name"),
    document_type: str = Query(..., description="Document type e.g. SOP, Policy"),
):
    return get_questionnaire_by_type(document_type=document_type, department=department)


@router.get("/{q_id}", summary="Get full questionnaire with all questions")
def get_one(q_id: str):
    return get_questionnaire(q_id)
# from fastapi import APIRouter, Query
# from typing import Optional
# from services.questionnaire_repository import list_questionnaires, get_questionnaire

# router = APIRouter()


# @router.get("/", summary="List all questionnaires")
# def list_all(
#     department: Optional[str] = Query(None, description="Filter by department"),
#     document_type: Optional[str] = Query(None, description="Filter by document type"),
# ):
#     return list_questionnaires(department=department, document_type=document_type)


# @router.get("/{q_id}", summary="Get a questionnaire by ID")
# def get_one(q_id: str):
#     return get_questionnaire(q_id)
# from fastapi import APIRouter
# from schemas.document_schema import QuestionnaireCreateRequest
# from services.questionnaire_repository import (
#     create_questionnaire,
#     list_questionnaires,
#     get_questionnaire,
#     delete_questionnaire,
# )

# router = APIRouter()




# @router.get("/", summary="List all questionnaires")
# def list_all():
#     return list_questionnaires()


# @router.get("/{q_id}", summary="Get a questionnaire by ID")
# def get_one(q_id: str):
#     return get_questionnaire(q_id)


# @router.delete("/{q_id}", summary="Delete a questionnaire by ID")
# def delete_one(q_id: str):
#     return delete_questionnaire(q_id)
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
