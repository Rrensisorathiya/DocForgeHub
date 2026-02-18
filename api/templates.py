from fastapi import APIRouter, HTTPException
from services.template_repository import (
    create_template,
    list_templates,
    get_template,
    update_template,
    delete_template,
)

router = APIRouter()

@router.post("/")
def create(payload: dict):
    return create_template(payload)

@router.get("/")
def list_all():
    return list_templates()

@router.get("/{template_id}")
def get_one(template_id: str):
    return get_template(template_id)

@router.put("/{template_id}")
def update_one(template_id: str, payload: dict):
    return update_template(template_id, payload)

@router.delete("/{template_id}")
def delete_one(template_id: str):
    return delete_template(template_id)
