"""
api/questionnaires.py
FastAPI router for questionnaire endpoints
"""

from __future__ import annotations

import json
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

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
# """
# api/questionnaires.py
# ---------------------
# FastAPI router for questionnaire endpoints.

# CRITICAL — Route ordering fix:
#   FastAPI matches routes top-to-bottom. The old code had GET /{q_id} at the
#   top, so requests to /full, /schema, /by-type etc. were matched as if "full"
#   or "schema" were integer IDs, causing:
#       psycopg2.errors.InvalidTextRepresentation:
#           invalid input syntax for type integer: "full"

#   Fix: ALL named sub-routes are declared BEFORE the /{q_id} catch-all.
#   The /{q_id} route is declared last with type hint `q_id: int` so FastAPI
#   will only route to it when the path segment is a valid integer.
# """

# from __future__ import annotations

# import json
# from typing import Any, Optional

# from fastapi import APIRouter, HTTPException, Query
# from pydantic import BaseModel

# # ── Schema helpers (loaded from JSON files) ───────────────────────────────────
# _SCHEMA_AVAILABLE = True
# _schema_import_err_msg: Optional[str] = None

# try:
#     from schemas.document_schema import (  # type: ignore
#         get_all_departments,
#         get_document_types,
#         get_common_questions,
#         get_metadata_questions,
#         get_document_questions,
#         get_all_questions,
#         get_required_metadata,
#         get_optional_metadata,
#         get_document_type_metadata,
#         get_document_status_types,
#         get_confidentiality_levels,
#         get_data_classification_types,
#         get_full_schema,
#         validate_department,
#         validate_document_type,
#         search_document_types,
#     )
#     _SCHEMA_AVAILABLE = True
# except Exception as _schema_import_err:
#     _SCHEMA_AVAILABLE = False
#     _schema_import_err_msg = str(_schema_import_err)
#     # Stub out every function so the module still loads
#     def _schema_unavailable(*args, **kwargs):
#         raise HTTPException(
#             status_code=503,
#             detail=(
#                 "Schema service unavailable. "
#                 "Ensure Schema/content.json, Schema/metadata.json, and "
#                 f"Schema/Question_Answer.json exist. Error: {_schema_import_err_msg}"
#             ),
#         )
#     get_all_departments = get_document_types = get_common_questions = _schema_unavailable
#     get_metadata_questions = get_document_questions = get_all_questions = _schema_unavailable
#     get_required_metadata = get_optional_metadata = get_document_type_metadata = _schema_unavailable
#     get_document_status_types = get_confidentiality_levels = _schema_unavailable
#     get_data_classification_types = get_full_schema = _schema_unavailable
#     search_document_types = _schema_unavailable
#     def validate_department(department: str) -> bool: return False  # type: ignore[misc]
#     def validate_document_type(department: str, document_type: str) -> bool: return False  # type: ignore[misc]

# # ── DB repository (existing) ──────────────────────────────────────────────────
# # Graceful imports: the live repository may not have all three functions yet.
# # Missing functions are replaced with safe stubs so the module always loads.
# try:
#     from services.questionnaire_repository import get_questionnaire  # type: ignore
# except ImportError:
#     def get_questionnaire(q_id):  # type: ignore[misc]
#         return None

# try:
#     from services.questionnaire_repository import list_questionnaires  # type: ignore
# except ImportError:
#     def list_questionnaires():  # type: ignore[misc]
#         return []

# try:
#     from services.questionnaire_repository import get_questionnaire_by_type  # type: ignore
#     _HAS_GET_BY_TYPE = True
# except ImportError:
#     _HAS_GET_BY_TYPE = False
#     def get_questionnaire_by_type(department, document_type):  # type: ignore[misc]
#         return None

# router = APIRouter(prefix="/questionnaires", tags=["Questionnaires"])


# # ═══════════════════════════════════════════════════════════════════════════════
# # ── DIAGNOSTIC ENDPOINT ── hit this first if you get 500s
# # ═══════════════════════════════════════════════════════════════════════════════

# @router.get("/status", summary="Check schema + repository availability")
# def get_status() -> dict:
#     """
#     Returns the health of both subsystems:
#       - schema_available : True if JSON schema files loaded OK
#       - repository_available : True if get_questionnaire_by_type exists in DB repo
#     If schema_available is False, check that Schema/ JSON files are in place.
#     """
#     return {
#         "schema_available":     _SCHEMA_AVAILABLE,
#         "schema_error":         _schema_import_err_msg if not _SCHEMA_AVAILABLE else None,
#         "repository_by_type":   _HAS_GET_BY_TYPE,
#         "note": (
#             "If schema_available=False: copy updated Schema/*.json files to the project. "
#             "If repository_by_type=False: /by-type falls back to JSON schema (harmless)."
#         ),
#     }


# # ═══════════════════════════════════════════════════════════════════════════════
# # Pydantic response models
# # ═══════════════════════════════════════════════════════════════════════════════

# class QuestionItem(BaseModel):
#     id: str
#     question: str
#     type: str = "text"
#     required: bool = False
#     options: list[str] = []
#     category: str = "common"


# class QuestionnaireResponse(BaseModel):
#     department: Optional[str] = None
#     document_type: Optional[str] = None
#     questions: list[QuestionItem]


# class DepartmentListResponse(BaseModel):
#     departments: list[str]
#     total: int


# class DocumentTypeListResponse(BaseModel):
#     department: str
#     document_types: list[str]
#     total: int


# class FullSchemaResponse(BaseModel):
#     department: str
#     document_type: str
#     sections: list[str]
#     required_metadata: list[str]
#     optional_metadata: list[str]
#     doc_type_metadata: list[str]
#     questions: list[QuestionItem]
#     status_types: list[str]
#     confidentiality_levels: list[str]
#     data_classification_types: list[str]


# class MetadataFieldsResponse(BaseModel):
#     department: str
#     required: list[str]
#     optional: list[str]
#     doc_type_specific: list[str] = []


# class SearchResult(BaseModel):
#     department: str
#     document_type: str


# # ═══════════════════════════════════════════════════════════════════════════════
# # Internal helpers
# # ═══════════════════════════════════════════════════════════════════════════════

# def _to_question_items(
#     raw: list[dict],
#     default_category: str = "common",
# ) -> list[QuestionItem]:
#     items = []
#     for q in raw:
#         items.append(QuestionItem(
#             id=q.get("id", ""),
#             question=q.get("question", ""),
#             type=q.get("type", "text"),
#             required=q.get("required", False),
#             options=q.get("options", []),
#             category=q.get("category", default_category),
#         ))
#     return items


# def _assert_department(department: str) -> None:
#     if not validate_department(department):
#         raise HTTPException(
#             status_code=404,
#             detail=(
#                 f"Department not found: {department!r}. "
#                 "Use GET /questionnaires/departments to list valid departments."
#             ),
#         )


# def _assert_document_type(department: str, document_type: str) -> None:
#     if not validate_document_type(department, document_type):
#         raise HTTPException(
#             status_code=404,
#             detail=(
#                 f"Document type {document_type!r} not found in {department!r}. "
#                 "Use GET /questionnaires/document-types?department=… to list valid types."
#             ),
#         )


# # ═══════════════════════════════════════════════════════════════════════════════
# # ── NAMED ROUTES  ── declared FIRST so FastAPI matches them before /{q_id}
# # ═══════════════════════════════════════════════════════════════════════════════

# @router.get(
#     "/departments",
#     response_model=DepartmentListResponse,
#     summary="List all 13 SaaS Enterprise departments",
# )
# def list_departments() -> DepartmentListResponse:
#     depts = get_all_departments()
#     return DepartmentListResponse(departments=depts, total=len(depts))


# @router.get(
#     "/document-types",
#     response_model=DocumentTypeListResponse,
#     summary="List document types for a department",
# )
# def list_document_types(
#     department: str = Query(..., description="Department name"),
# ) -> DocumentTypeListResponse:
#     _assert_department(department)
#     doc_types = get_document_types(department)
#     return DocumentTypeListResponse(
#         department=department,
#         document_types=doc_types,
#         total=len(doc_types),
#     )


# @router.get(
#     "/full",
#     response_model=QuestionnaireResponse,
#     summary="Get all questions — common + metadata + document-specific",
# )
# def get_full_questionnaire(
#     department: str    = Query(..., description="Department name"),
#     document_type: str = Query(..., description="Document type name"),
# ) -> QuestionnaireResponse:
#     """
#     Returns the complete ordered question set for a document generation flow:
#       1. Common department questions   (category: common)
#       2. Metadata questions            (category: metadata)
#       3. Document-type-specific        (category: document_type_specific)
#     """
#     _assert_department(department)
#     _assert_document_type(department, document_type)

#     common_qs   = _to_question_items(get_common_questions(department),   "common")
#     metadata_qs = _to_question_items(get_metadata_questions(department), "metadata")
#     doc_qs      = _to_question_items(
#         get_document_questions(department, document_type), "document_type_specific"
#     )

#     return QuestionnaireResponse(
#         department=department,
#         document_type=document_type,
#         questions=common_qs + metadata_qs + doc_qs,
#     )


# @router.get(
#     "/schema",
#     response_model=FullSchemaResponse,
#     summary="Get complete schema — sections + metadata fields + questions + enums",
# )
# def get_schema(
#     department: str    = Query(..., description="Department name"),
#     document_type: str = Query(..., description="Document type name"),
# ) -> FullSchemaResponse:
#     _assert_department(department)
#     _assert_document_type(department, document_type)

#     bundle = get_full_schema(department, document_type)

#     common_qs   = _to_question_items(get_common_questions(department),   "common")
#     metadata_qs = _to_question_items(get_metadata_questions(department), "metadata")
#     doc_qs      = _to_question_items(
#         get_document_questions(department, document_type), "document_type_specific"
#     )

#     return FullSchemaResponse(
#         department=bundle["department"],
#         document_type=bundle["document_type"],
#         sections=bundle["sections"],
#         required_metadata=bundle["required_metadata"],
#         optional_metadata=bundle["optional_metadata"],
#         doc_type_metadata=bundle["doc_type_metadata"],
#         questions=common_qs + metadata_qs + doc_qs,
#         status_types=bundle["status_types"],
#         confidentiality_levels=bundle["confidentiality_levels"],
#         data_classification_types=bundle["data_classification_types"],
#     )


# @router.get(
#     "/by-type",
#     response_model=QuestionnaireResponse,
#     summary="Get questionnaire by department + document type (DB-first, schema fallback)",
# )
# def get_by_type(
#     department: str    = Query(..., description="Department name"),
#     document_type: str = Query(..., description="Document type name"),
# ) -> QuestionnaireResponse:
#     """
#     1. Tries to fetch from the DB via questionnaire_repository.
#     2. Falls back to JSON schema if nothing found in DB.
#     """
#     # DB-first
#     try:
#         db_result = get_questionnaire_by_type(department, document_type)
#         if db_result and db_result.get("questions"):
#             qs = db_result["questions"]
#             if isinstance(qs, str):
#                 qs = json.loads(qs)
#             items = []
#             for q in qs:
#                 items.append(QuestionItem(
#                     id=q.get("id", ""),
#                     question=q.get("question", ""),
#                     type=q.get("type", "text"),
#                     required=q.get("required", False),
#                     options=q.get("options", []),
#                     category=q.get("category", "common"),
#                 ))
#             return QuestionnaireResponse(
#                 department=department,
#                 document_type=document_type,
#                 questions=items,
#             )
#     except Exception:
#         pass  # fall through to schema-based

#     # Schema fallback
#     _assert_department(department)
#     _assert_document_type(department, document_type)

#     common_qs   = _to_question_items(get_common_questions(department),   "common")
#     metadata_qs = _to_question_items(get_metadata_questions(department), "metadata")
#     doc_qs      = _to_question_items(
#         get_document_questions(department, document_type), "document_type_specific"
#     )

#     return QuestionnaireResponse(
#         department=department,
#         document_type=document_type,
#         questions=common_qs + metadata_qs + doc_qs,
#     )


# @router.get(
#     "/common",
#     response_model=QuestionnaireResponse,
#     summary="Get common questions for a department",
# )
# def get_common(
#     department: str = Query(..., description="Department name"),
# ) -> QuestionnaireResponse:
#     _assert_department(department)
#     return QuestionnaireResponse(
#         department=department,
#         questions=_to_question_items(get_common_questions(department), "common"),
#     )


# @router.get(
#     "/metadata-questions",
#     response_model=QuestionnaireResponse,
#     summary="Get metadata questions for a department",
# )
# def get_metadata_qs(
#     department: str = Query(..., description="Department name"),
# ) -> QuestionnaireResponse:
#     _assert_department(department)
#     return QuestionnaireResponse(
#         department=department,
#         questions=_to_question_items(get_metadata_questions(department), "metadata"),
#     )


# @router.get(
#     "/document-questions",
#     response_model=QuestionnaireResponse,
#     summary="Get document-type-specific questions",
# )
# def get_doc_questions(
#     department: str    = Query(..., description="Department name"),
#     document_type: str = Query(..., description="Document type name"),
# ) -> QuestionnaireResponse:
#     _assert_department(department)
#     _assert_document_type(department, document_type)
#     return QuestionnaireResponse(
#         department=department,
#         document_type=document_type,
#         questions=_to_question_items(
#             get_document_questions(department, document_type),
#             "document_type_specific",
#         ),
#     )


# @router.get(
#     "/metadata-fields",
#     response_model=MetadataFieldsResponse,
#     summary="Get metadata field definitions",
# )
# def get_metadata_fields(
#     department: str              = Query(..., description="Department name"),
#     document_type: Optional[str] = Query(None, description="Optional document type"),
# ) -> MetadataFieldsResponse:
#     _assert_department(department)
#     doc_type_specific = []
#     if document_type:
#         _assert_document_type(department, document_type)
#         doc_type_specific = get_document_type_metadata(department, document_type)

#     return MetadataFieldsResponse(
#         department=department,
#         required=get_required_metadata(department),
#         optional=get_optional_metadata(department),
#         doc_type_specific=doc_type_specific,
#     )


# @router.get(
#     "/enums",
#     response_model=dict,
#     summary="Get enum / dropdown values for a department",
# )
# def get_enum_values(
#     department: str = Query(..., description="Department name"),
# ) -> dict:
#     _assert_department(department)
#     return {
#         "document_status_types":     get_document_status_types(department),
#         "confidentiality_levels":    get_confidentiality_levels(department),
#         "data_classification_types": get_data_classification_types(department),
#     }


# @router.get(
#     "/search",
#     response_model=list[SearchResult],
#     summary="Search document types across all departments",
# )
# def search(
#     q: str = Query(..., min_length=2, description="Search term"),
# ) -> list[SearchResult]:
#     results = search_document_types(q)
#     return [SearchResult(**r) for r in results]


# @router.get(
#     "/",
#     summary="List all questionnaires stored in the database",
# )
# def list_all():
#     try:
#         return list_questionnaires()
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# # ═══════════════════════════════════════════════════════════════════════════════
# # ── INTEGER CATCH-ALL  ── declared LAST so named routes above take priority
# # ═══════════════════════════════════════════════════════════════════════════════

# @router.get(
#     "/{q_id}",
#     summary="Get a single questionnaire by integer DB primary key",
# )
# def get_one(q_id: int):
#     """
#     Fetch a questionnaire record by its database integer primary key.

#     This route is intentionally declared LAST.  FastAPI will only reach it
#     when the path segment is a valid integer (e.g. /questionnaires/42).
#     String paths like /questionnaires/full or /questionnaires/schema are
#     matched by their own named routes above and never reach this handler.
#     """
#     try:
#         result = get_questionnaire(q_id)
#         if not result:
#             raise HTTPException(
#                 status_code=404,
#                 detail=f"Questionnaire with id={q_id} not found.",
#             )
#         return result
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

#------------------------------------------------------------------------------------------
# from fastapi import APIRouter, Query
# from typing import Optional
# from services.questionnaire_repository import list_questionnaires, get_questionnaire, get_questionnaire_by_type

# router = APIRouter()


# @router.get("/", summary="List all questionnaires (seeded from Question_Answer.json)")
# def list_all(
#     department: Optional[str] = Query(None, description="Filter by department"),
#     document_type: Optional[str] = Query(None, description="Filter by document type"),
# ):
#     return list_questionnaires(department=department, document_type=document_type)


# @router.get("/by-type", summary="Get questionnaire by department and document type")
# def get_by_type(
#     department: str = Query(..., description="Department name"),
#     document_type: str = Query(..., description="Document type e.g. SOP, Policy"),
# ):
#     return get_questionnaire_by_type(document_type=document_type, department=department)


# @router.get("/{q_id}", summary="Get full questionnaire with all questions")
# def get_one(q_id: str):
#     return get_questionnaire(q_id)



#-----------------------------------------------------------------------------------------

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
