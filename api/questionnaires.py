"""
api/questionnaires.py
FastAPI router for questionnaire endpoints
"""

from __future__ import annotations

import json
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from utils.logger import setup_logger

logger = setup_logger(__name__)

from schemas.document_schema import (
    get_all_departments,
    get_document_types,
    get_common_questions,
    get_metadata_questions,
    get_document_questions,
    get_full_schema,
    get_required_metadata,
    get_optional_metadata,
    get_document_type_metadata,
    validate_department,
    validate_document_type,
)

from services.questionnaire_repository import (
    get_questionnaire,
    list_questionnaires,
    get_questionnaire_by_type,
)

router = APIRouter(prefix="/questionnaires", tags=["Questionnaires"])


# ------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------

class QuestionItem(BaseModel):
    id: str
    question: str
    type: str = "text"
    required: bool = False
    options: List[str] = []
    category: str = "common"


class QuestionnaireResponse(BaseModel):
    department: Optional[str] = None
    document_type: Optional[str] = None
    questions: List[QuestionItem]


class DepartmentListResponse(BaseModel):
    departments: List[str]
    total: int


class DocumentTypeListResponse(BaseModel):
    department: str
    document_types: List[str]
    total: int


class MetadataFieldsResponse(BaseModel):
    department: str
    required: List[str]
    optional: List[str]
    doc_type_specific: List[str]


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def convert_questions(raw):
    items = []
    for q in raw:
        items.append(
            QuestionItem(
                id=q.get("id", ""),
                question=q.get("question", ""),
                type=q.get("type", "text"),
                required=q.get("required", False),
                options=q.get("options", []),
                category=q.get("category", "common"),
            )
        )
    return items


# ------------------------------------------------------------
# Health Check
# ------------------------------------------------------------

@router.get("/status")
def status():
    return {
        "status": "ok",
        "message": "Questionnaire API running"
    }


# ------------------------------------------------------------
# Departments
# ------------------------------------------------------------

@router.get("/departments", response_model=DepartmentListResponse)
def list_departments():
    departments = get_all_departments()

    return DepartmentListResponse(
        departments=departments,
        total=len(departments),
    )


# ------------------------------------------------------------
# Document Types
# ------------------------------------------------------------

@router.get("/document-types", response_model=DocumentTypeListResponse)
def document_types(
    department: str = Query(...),
):
    if not validate_department(department):
        raise HTTPException(status_code=404, detail="Invalid department")

    types = get_document_types(department)

    return DocumentTypeListResponse(
        department=department,
        document_types=types,
        total=len(types),
    )


# ------------------------------------------------------------
# FULL QUESTION SET
# ------------------------------------------------------------

@router.get("/full", response_model=QuestionnaireResponse)
def full_questionnaire(
    department: str,
    document_type: str,
):

    if not validate_department(department):
        raise HTTPException(status_code=404, detail="Invalid department")

    if not validate_document_type(department, document_type):
        raise HTTPException(status_code=404, detail="Invalid document type")

    common = convert_questions(get_common_questions(department))
    metadata = convert_questions(get_metadata_questions(department))
    doc = convert_questions(get_document_questions(department, document_type))

    return QuestionnaireResponse(
        department=department,
        document_type=document_type,
        questions=common + metadata + doc,
    )


# ------------------------------------------------------------
# SCHEMA ENDPOINT
# ------------------------------------------------------------

@router.get("/schema")
def schema(
    department: str,
    document_type: str,
):

    if not validate_department(department):
        raise HTTPException(status_code=404, detail="Invalid department")

    if not validate_document_type(department, document_type):
        raise HTTPException(status_code=404, detail="Invalid document type")

    schema = get_full_schema(department, document_type)

    questions = (
        convert_questions(get_common_questions(department))
        + convert_questions(get_metadata_questions(department))
        + convert_questions(get_document_questions(department, document_type))
    )

    schema["questions"] = questions

    return schema


# ------------------------------------------------------------
# BY TYPE
# ------------------------------------------------------------

@router.get("/by-type", response_model=QuestionnaireResponse)
def by_type(
    department: str,
    document_type: str,
):

    try:
        db_data = get_questionnaire_by_type(department, document_type)

        if db_data and db_data.get("questions"):
            qs = db_data["questions"]

            if isinstance(qs, str):
                qs = json.loads(qs)

            return QuestionnaireResponse(
                department=department,
                document_type=document_type,
                questions=convert_questions(qs),
            )

    except Exception:
        pass

    # fallback schema
    return full_questionnaire(department, document_type)


# ------------------------------------------------------------
# Metadata Fields
# ------------------------------------------------------------

@router.get("/metadata-fields", response_model=MetadataFieldsResponse)
def metadata_fields(
    department: str,
    document_type: Optional[str] = None,
):

    if not validate_department(department):
        raise HTTPException(status_code=404, detail="Invalid department")

    doc_specific = []

    if document_type:
        doc_specific = get_document_type_metadata(department, document_type)

    return MetadataFieldsResponse(
        department=department,
        required=get_required_metadata(department),
        optional=get_optional_metadata(department),
        doc_type_specific=doc_specific,
    )


# ------------------------------------------------------------
# List all questionnaires
# ------------------------------------------------------------

@router.get("/")
def list_all():
    return list_questionnaires()


# ------------------------------------------------------------
# Get single questionnaire
# ------------------------------------------------------------

@router.get("/{q_id}")
def get_one(q_id: int):

    q = get_questionnaire(q_id)

    if not q:
        raise HTTPException(status_code=404, detail="Questionnaire not found")

    return q
