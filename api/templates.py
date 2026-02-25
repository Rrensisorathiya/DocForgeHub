from fastapi import APIRouter, Query
from typing import Optional
from services.template_repository import list_templates, get_template
from db import get_connection

router = APIRouter()


@router.get("/", summary="List all templates (seeded from content.json)")
def list_all(
    department: Optional[str] = Query(None, description="Filter by department"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
):
    return list_templates(department=department, document_type=document_type)


@router.get("/departments", summary="List all departments that have templates")
def list_departments():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT department FROM templates ORDER BY department")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return {"departments": [r[0] for r in rows]}


@router.get("/document-types", summary="List all document types available")
def list_document_types():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT document_type FROM templates ORDER BY document_type")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return {"document_types": [r[0] for r in rows]}


@router.get("/{template_id}", summary="Get full template with all sections")
def get_one(template_id: str):
    return get_template(template_id)
# from fastapi import APIRouter, Query
# from typing import Optional
# from services.template_repository import list_templates, get_template

# router = APIRouter()


# @router.get("/", summary="List all templates")
# def list_all(
#     department: Optional[str] = Query(None, description="Filter by department"),
#     document_type: Optional[str] = Query(None, description="Filter by document type"),
# ):
#     return list_templates(department=department, document_type=document_type)


# @router.get("/{template_id}", summary="Get a template by ID")
# def get_one(template_id: str):
#     return get_template(template_id)
# from fastapi import APIRouter
# from schemas.document_schema import TemplateCreateRequest, TemplateUpdateRequest
# from services.template_repository import (
#     create_template,
#     list_templates,
#     get_template,
#     update_template,
#     delete_template,
# )

# router = APIRouter()



# @router.get("/", summary="List all templates")
# def list_all():
#     return list_templates()


# @router.get("/{template_id}", summary="Get a template by ID")
# def get_one(template_id: str):
#     return get_template(template_id)


# @router.put("/{template_id}", summary="Update a template's structure")
# def update_one(template_id: str, payload: TemplateUpdateRequest):
#     return update_template(template_id, payload.dict())


# @router.delete("/{template_id}", summary="Delete a template by ID")
# def delete_one(template_id: str):
#     return delete_template(template_id)
# from fastapi import APIRouter, HTTPException
# from services.template_repository import (
#     create_template,
#     list_templates,
#     get_template,
#     update_template,
#     delete_template,
# )

# router = APIRouter()

# @router.post("/")
# def create(payload: dict):
#     return create_template(payload)

# @router.get("/")
# def list_all():
#     return list_templates()

# @router.get("/{template_id}")
# def get_one(template_id: str):
#     return get_template(template_id)

# @router.put("/{template_id}")
# def update_one(template_id: str, payload: dict):
#     return update_template(template_id, payload)

# @router.delete("/{template_id}")
# def delete_one(template_id: str):
#     return delete_template(template_id)
