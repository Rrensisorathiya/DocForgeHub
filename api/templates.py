from fastapi import APIRouter
from schemas.document_schema import TemplateCreateRequest, TemplateUpdateRequest
from services.template_repository import (
    create_template,
    list_templates,
    get_template,
    update_template,
    delete_template,
)

router = APIRouter()


@router.post("/", summary="Create a new template")
def create(payload: TemplateCreateRequest):
    """
    Create a document template with sections.

    Example structure:
    ```json
    {
      "document_type": "SOP",
      "department": "HR",
      "structure": {
        "sections": ["Purpose", "Scope", "Process Steps"]
      }
    }
    ```
    """
    return create_template(payload.dict())


@router.get("/", summary="List all templates")
def list_all():
    return list_templates()


@router.get("/{template_id}", summary="Get a template by ID")
def get_one(template_id: str):
    return get_template(template_id)


@router.put("/{template_id}", summary="Update a template's structure")
def update_one(template_id: str, payload: TemplateUpdateRequest):
    return update_template(template_id, payload.dict())


@router.delete("/{template_id}", summary="Delete a template by ID")
def delete_one(template_id: str):
    return delete_template(template_id)
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
