from fastapi import APIRouter
from services.questionnaire_repository import (
    create_questionnaire,
    list_questionnaires,
    get_questionnaire,
    delete_questionnaire,
)

router = APIRouter()

@router.post("/")
def create(payload: dict):
    return create_questionnaire(payload)

@router.get("/")
def list_all():
    return list_questionnaires()

@router.get("/{q_id}")
def get_one(q_id: str):
    return get_questionnaire(q_id)

@router.delete("/{q_id}")
def delete_one(q_id: str):
    return delete_questionnaire(q_id)
