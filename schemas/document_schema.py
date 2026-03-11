"""
schemas/document_schema.py
--------------------------
Loads ALL schema data from:
  - Schema/content.json          → departments, document types, sections
  - Schema/Question_Answer.json  → questions (old dict OR new list format)
  - Schema/metadata.json         → metadata fields, enums (optional)

All functions imported by api/questionnaires.py and api/documents.py
are implemented here.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from pydantic import BaseModel


# ── Pydantic models (imported by api/documents.py) ────────────────────────────

class DocumentGenerateRequest(BaseModel):
    department:      str
    document_type:   str
    industry:        str = "SaaS"
    question_answers: Dict[str, Any] = {}

# ── Resolve paths ──────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCHEMA_DIR = os.path.join(_BASE_DIR, "Schema")

_CONTENT_PATH  = os.path.join(_SCHEMA_DIR, "content.json")
_QA_PATH       = os.path.join(_SCHEMA_DIR, "Question_Answer.json")
_META_PATH     = os.path.join(_SCHEMA_DIR, "metadata.json")   # optional


# ── Load JSON files at import time ─────────────────────────────────────────────

def _load_json(path: str, required: bool = True) -> Any:
    if not os.path.exists(path):
        if required:
            raise FileNotFoundError(
                f"Required schema file not found: {path}\n"
                f"Place the file in the Schema/ folder and restart uvicorn."
            )
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


_content_raw: list[dict] = _load_json(_CONTENT_PATH, required=True)
_qa_raw:      Any        = _load_json(_QA_PATH,      required=True)
_meta_raw:    Any        = _load_json(_META_PATH,     required=False)  # optional


# ── Normalise QA format — supports OLD dict AND NEW list ──────────────────────
#
# OLD format (dict):  { "user_qa_schema": { "question_types": [...] } }
#   Each entry has: document_type, department, questions (flat list)
#
# NEW format (list):  [ { department, common_questions,
#                          metadata_questions, document_questions }, ... ]

def _normalise_qa_to_list(raw: Any) -> list[dict]:
    """
    Accept either format and return a canonical list where each entry has:
      department, common_questions, metadata_questions, document_questions
    """
    # ── NEW format: already a list ────────────────────────────────────────────
    if isinstance(raw, list):
        return raw

    # ── OLD format: dict with user_qa_schema key ──────────────────────────────
    if isinstance(raw, dict):
        # Try to find question entries — old schema may use various keys
        entries = (
            raw.get("user_qa_schema", {}).get("question_types")
            or raw.get("questionnaires")
            or raw.get("questions")
            or []
        )

        if not entries:
            # Fallback: treat top-level dict values as entries
            entries = list(raw.values()) if raw else []

        # Group flat entries by department into new format
        dept_map: dict[str, dict] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            dept = entry.get("department", "Unknown").strip()
            doc_type = entry.get("document_type", "").strip()
            questions = entry.get("questions", [])

            if dept not in dept_map:
                dept_map[dept] = {
                    "department":         dept,
                    "common_questions":   [],
                    "metadata_questions": [],
                    "document_questions": {},
                }

            if doc_type:
                dept_map[dept]["document_questions"][doc_type] = questions
            else:
                # No doc_type → treat as common questions
                dept_map[dept]["common_questions"].extend(questions)

        return list(dept_map.values())

    return []  # unrecognised format — return empty, endpoints will return []


_qa_list: list[dict] = _normalise_qa_to_list(_qa_raw)


# ── Build lookup structures ────────────────────────────────────────────────────

# content.json  →  { department: { doc_type: { sections: [...] } } }
_dept_content: dict[str, dict[str, dict]] = {}
for _dept_obj in _content_raw:
    _dept = _dept_obj.get("department", "").strip()
    if _dept:
        _dept_content[_dept] = _dept_obj.get("documents", {})


# Question_Answer.json (normalised list format)
# →  { department: { common_questions, metadata_questions, document_questions } }
_dept_qa: dict[str, dict] = {}
for _entry in _qa_list:
    _dept = _entry.get("department", "").strip()
    if _dept:
        _dept_qa[_dept] = {
            "common_questions":   _entry.get("common_questions",   []),
            "metadata_questions": _entry.get("metadata_questions", []),
            "document_questions": _entry.get("document_questions", {}),
        }


# metadata.json  →  per-department metadata config (optional)
# If absent, sensible defaults are returned for all metadata endpoints.
_dept_meta: dict[str, dict] = {}
if _meta_raw:
    if isinstance(_meta_raw, list):
        for _m in _meta_raw:
            _d = _m.get("department", "").strip()
            if _d:
                _dept_meta[_d] = _m
    elif isinstance(_meta_raw, dict):
        _dept_meta = _meta_raw


# ── Default enum values (used when metadata.json is absent) ───────────────────

_DEFAULT_STATUS_TYPES = [
    "Draft", "In Review", "Approved", "Published",
    "Archived", "Deprecated", "Superseded",
]

_DEFAULT_CONFIDENTIALITY = [
    "Public", "Internal", "Confidential",
    "Restricted", "Top Secret",
]

_DEFAULT_DATA_CLASSIFICATION = [
    "Public", "Internal Use Only", "Confidential",
    "Sensitive", "Restricted", "PII", "PCI", "PHI",
]

_DEFAULT_REQUIRED_METADATA = [
    "title", "document_type", "department",
    "version", "status", "created_by",
]

_DEFAULT_OPTIONAL_METADATA = [
    "reviewer", "approved_by", "approval_date",
    "effective_date", "expiry_date", "review_frequency",
    "tags", "compliance_tags", "audience",
    "priority", "confidentiality", "industry",
]


# ══════════════════════════════════════════════════════════════════════════════
# Public API — all functions imported by api/questionnaires.py
# ══════════════════════════════════════════════════════════════════════════════

def get_all_departments() -> list[str]:
    """Return sorted list of all department names."""
    return sorted(_dept_content.keys())


def get_document_types(department: str) -> list[str]:
    """Return document type names for a department (sorted)."""
    dept_docs = _dept_content.get(department, {})
    return sorted(dept_docs.keys())


def validate_department(department: str) -> bool:
    """True if department exists in content.json."""
    return department in _dept_content


def validate_document_type(department: str, document_type: str) -> bool:
    """True if document_type exists for the given department."""
    return document_type in _dept_content.get(department, {})


def search_document_types(query: str) -> list[dict]:
    """
    Case-insensitive substring search across all departments × document types.
    Returns list of { department, document_type } dicts.
    """
    q = query.lower()
    results = []
    for dept, docs in _dept_content.items():
        for doc_type in docs:
            if q in doc_type.lower() or q in dept.lower():
                results.append({"department": dept, "document_type": doc_type})
    return sorted(results, key=lambda x: (x["department"], x["document_type"]))


# ── Question helpers ───────────────────────────────────────────────────────────

def _normalise_questions(raw: list[dict], category: str) -> list[dict]:
    """Ensure every question dict has all expected keys."""
    out = []
    for q in raw:
        out.append({
            "id":             q.get("id", ""),
            "question":       q.get("question", ""),
            "type":           q.get("type", "text"),
            "required":       q.get("required", False),
            "options":        q.get("options", []),
            "placeholder":    q.get("placeholder", ""),
            "used_in_prompt": q.get("used_in_prompt", ""),
            "category":       category,
        })
    return out


def get_common_questions(department: str) -> list[dict]:
    """Common questions shared across all document types in this department."""
    raw = _dept_qa.get(department, {}).get("common_questions", [])
    return _normalise_questions(raw, "common")


def get_metadata_questions(department: str) -> list[dict]:
    """Metadata questions for a department."""
    raw = _dept_qa.get(department, {}).get("metadata_questions", [])
    return _normalise_questions(raw, "metadata")


def get_document_questions(department: str, document_type: str) -> list[dict]:
    """Document-type-specific questions for a (department, document_type) pair."""
    doc_qs_map = _dept_qa.get(department, {}).get("document_questions", {})
    raw = doc_qs_map.get(document_type, [])
    return _normalise_questions(raw, "document_type_specific")


def get_all_questions(department: str, document_type: str) -> list[dict]:
    """
    Full ordered question list:
      1. common  2. metadata  3. document_type_specific
    """
    return (
        get_common_questions(department)
        + get_metadata_questions(department)
        + get_document_questions(department, document_type)
    )


# ── Sections ───────────────────────────────────────────────────────────────────

def get_sections(department: str, document_type: str) -> list[str]:
    """Section names from content.json for a (department, document_type)."""
    raw = (
        _dept_content
        .get(department, {})
        .get(document_type, {})
        .get("sections", [])
    )
    return [s for s in raw if isinstance(s, str)]


# ── Metadata field helpers ─────────────────────────────────────────────────────

def get_required_metadata(department: str) -> list[str]:
    dept_meta = _dept_meta.get(department, {})
    return dept_meta.get("required_metadata", _DEFAULT_REQUIRED_METADATA)


def get_optional_metadata(department: str) -> list[str]:
    dept_meta = _dept_meta.get(department, {})
    return dept_meta.get("optional_metadata", _DEFAULT_OPTIONAL_METADATA)


def get_document_type_metadata(department: str, document_type: str) -> list[str]:
    dept_meta = _dept_meta.get(department, {})
    doc_meta = dept_meta.get("document_type_metadata", {})
    return doc_meta.get(document_type, [])


# ── Enum helpers ───────────────────────────────────────────────────────────────

def get_document_status_types(department: str) -> list[str]:
    dept_meta = _dept_meta.get(department, {})
    return dept_meta.get("status_types", _DEFAULT_STATUS_TYPES)


def get_confidentiality_levels(department: str) -> list[str]:
    dept_meta = _dept_meta.get(department, {})
    return dept_meta.get("confidentiality_levels", _DEFAULT_CONFIDENTIALITY)


def get_data_classification_types(department: str) -> list[str]:
    dept_meta = _dept_meta.get(department, {})
    return dept_meta.get("data_classification_types", _DEFAULT_DATA_CLASSIFICATION)


# ── Full schema bundle ─────────────────────────────────────────────────────────

def get_full_schema(department: str, document_type: str) -> dict:
    """
    Returns everything needed for the /schema endpoint in one call.
    """
    return {
        "department":              department,
        "document_type":           document_type,
        "sections":                get_sections(department, document_type),
        "required_metadata":       get_required_metadata(department),
        "optional_metadata":       get_optional_metadata(department),
        "doc_type_metadata":       get_document_type_metadata(department, document_type),
        "questions":               get_all_questions(department, document_type),
        "status_types":            get_document_status_types(department),
        "confidentiality_levels":  get_confidentiality_levels(department),
        "data_classification_types": get_data_classification_types(department),
    }
# """
# schemas/document_schema.py
# --------------------------
# Loads ALL schema data from:
#   - Schema/content.json          → departments, document types, sections
#   - Schema/Question_Answer.json  → questions (new LIST format)
#   - Schema/metadata.json         → metadata fields, enums (optional)

# All functions imported by api/questionnaires.py are implemented here.
# If a JSON file is missing, a clear error is raised at import time
# (not silently swallowed), so the 503 stub in questionnaires.py fires
# with a meaningful message.
# """

# from __future__ import annotations

# import json
# import os
# from typing import Any

# # ── Resolve paths ──────────────────────────────────────────────────────────────
# _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# _SCHEMA_DIR = os.path.join(_BASE_DIR, "Schema")

# _CONTENT_PATH  = os.path.join(_SCHEMA_DIR, "content.json")
# _QA_PATH       = os.path.join(_SCHEMA_DIR, "Question_Answer.json")
# _META_PATH     = os.path.join(_SCHEMA_DIR, "metadata.json")   # optional


# # ── Load JSON files at import time ─────────────────────────────────────────────

# def _load_json(path: str, required: bool = True) -> Any:
#     if not os.path.exists(path):
#         if required:
#             raise FileNotFoundError(
#                 f"Required schema file not found: {path}\n"
#                 f"Place the file in the Schema/ folder and restart uvicorn."
#             )
#         return None
#     with open(path, "r", encoding="utf-8") as f:
#         return json.load(f)


# _content_raw: list[dict] = _load_json(_CONTENT_PATH, required=True)
# _qa_raw:      Any        = _load_json(_QA_PATH,      required=True)
# _meta_raw:    Any        = _load_json(_META_PATH,     required=False)  # optional


# # ── Validate QA format ─────────────────────────────────────────────────────────

# if isinstance(_qa_raw, dict):
#     raise ValueError(
#         "Question_Answer.json is in OLD dict format (has 'user_qa_schema' key).\n"
#         "Replace Schema/Question_Answer.json with the new LIST-format file.\n"
#         "Each entry must have: department, common_questions, metadata_questions, document_questions."
#     )

# if not isinstance(_qa_raw, list):
#     raise ValueError("Question_Answer.json must be a JSON array (list).")


# # ── Build lookup structures ────────────────────────────────────────────────────

# # content.json  →  { department: { doc_type: { sections: [...] } } }
# _dept_content: dict[str, dict[str, dict]] = {}
# for _dept_obj in _content_raw:
#     _dept = _dept_obj.get("department", "").strip()
#     if _dept:
#         _dept_content[_dept] = _dept_obj.get("documents", {})


# # Question_Answer.json (new list format)
# # →  { department: { common_questions, metadata_questions, document_questions } }
# _dept_qa: dict[str, dict] = {}
# for _entry in _qa_raw:
#     _dept = _entry.get("department", "").strip()
#     if _dept:
#         _dept_qa[_dept] = {
#             "common_questions":   _entry.get("common_questions",   []),
#             "metadata_questions": _entry.get("metadata_questions", []),
#             "document_questions": _entry.get("document_questions", {}),
#         }


# # metadata.json  →  per-department metadata config (optional)
# # If absent, sensible defaults are returned for all metadata endpoints.
# _dept_meta: dict[str, dict] = {}
# if _meta_raw:
#     if isinstance(_meta_raw, list):
#         for _m in _meta_raw:
#             _d = _m.get("department", "").strip()
#             if _d:
#                 _dept_meta[_d] = _m
#     elif isinstance(_meta_raw, dict):
#         _dept_meta = _meta_raw


# # ── Default enum values (used when metadata.json is absent) ───────────────────

# _DEFAULT_STATUS_TYPES = [
#     "Draft", "In Review", "Approved", "Published",
#     "Archived", "Deprecated", "Superseded",
# ]

# _DEFAULT_CONFIDENTIALITY = [
#     "Public", "Internal", "Confidential",
#     "Restricted", "Top Secret",
# ]

# _DEFAULT_DATA_CLASSIFICATION = [
#     "Public", "Internal Use Only", "Confidential",
#     "Sensitive", "Restricted", "PII", "PCI", "PHI",
# ]

# _DEFAULT_REQUIRED_METADATA = [
#     "title", "document_type", "department",
#     "version", "status", "created_by",
# ]

# _DEFAULT_OPTIONAL_METADATA = [
#     "reviewer", "approved_by", "approval_date",
#     "effective_date", "expiry_date", "review_frequency",
#     "tags", "compliance_tags", "audience",
#     "priority", "confidentiality", "industry",
# ]


# # ══════════════════════════════════════════════════════════════════════════════
# # Public API — all functions imported by api/questionnaires.py
# # ══════════════════════════════════════════════════════════════════════════════

# def get_all_departments() -> list[str]:
#     """Return sorted list of all department names."""
#     return sorted(_dept_content.keys())


# def get_document_types(department: str) -> list[str]:
#     """Return document type names for a department (sorted)."""
#     dept_docs = _dept_content.get(department, {})
#     return sorted(dept_docs.keys())


# def validate_department(department: str) -> bool:
#     """True if department exists in content.json."""
#     return department in _dept_content


# def validate_document_type(department: str, document_type: str) -> bool:
#     """True if document_type exists for the given department."""
#     return document_type in _dept_content.get(department, {})


# def search_document_types(query: str) -> list[dict]:
#     """
#     Case-insensitive substring search across all departments × document types.
#     Returns list of { department, document_type } dicts.
#     """
#     q = query.lower()
#     results = []
#     for dept, docs in _dept_content.items():
#         for doc_type in docs:
#             if q in doc_type.lower() or q in dept.lower():
#                 results.append({"department": dept, "document_type": doc_type})
#     return sorted(results, key=lambda x: (x["department"], x["document_type"]))


# # ── Question helpers ───────────────────────────────────────────────────────────

# def _normalise_questions(raw: list[dict], category: str) -> list[dict]:
#     """Ensure every question dict has all expected keys."""
#     out = []
#     for q in raw:
#         out.append({
#             "id":             q.get("id", ""),
#             "question":       q.get("question", ""),
#             "type":           q.get("type", "text"),
#             "required":       q.get("required", False),
#             "options":        q.get("options", []),
#             "placeholder":    q.get("placeholder", ""),
#             "used_in_prompt": q.get("used_in_prompt", ""),
#             "category":       category,
#         })
#     return out


# def get_common_questions(department: str) -> list[dict]:
#     """Common questions shared across all document types in this department."""
#     raw = _dept_qa.get(department, {}).get("common_questions", [])
#     return _normalise_questions(raw, "common")


# def get_metadata_questions(department: str) -> list[dict]:
#     """Metadata questions for a department."""
#     raw = _dept_qa.get(department, {}).get("metadata_questions", [])
#     return _normalise_questions(raw, "metadata")


# def get_document_questions(department: str, document_type: str) -> list[dict]:
#     """Document-type-specific questions for a (department, document_type) pair."""
#     doc_qs_map = _dept_qa.get(department, {}).get("document_questions", {})
#     raw = doc_qs_map.get(document_type, [])
#     return _normalise_questions(raw, "document_type_specific")


# def get_all_questions(department: str, document_type: str) -> list[dict]:
#     """
#     Full ordered question list:
#       1. common  2. metadata  3. document_type_specific
#     """
#     return (
#         get_common_questions(department)
#         + get_metadata_questions(department)
#         + get_document_questions(department, document_type)
#     )


# # ── Sections ───────────────────────────────────────────────────────────────────

# def get_sections(department: str, document_type: str) -> list[str]:
#     """Section names from content.json for a (department, document_type)."""
#     raw = (
#         _dept_content
#         .get(department, {})
#         .get(document_type, {})
#         .get("sections", [])
#     )
#     return [s for s in raw if isinstance(s, str)]


# # ── Metadata field helpers ─────────────────────────────────────────────────────

# def get_required_metadata(department: str) -> list[str]:
#     dept_meta = _dept_meta.get(department, {})
#     return dept_meta.get("required_metadata", _DEFAULT_REQUIRED_METADATA)


# def get_optional_metadata(department: str) -> list[str]:
#     dept_meta = _dept_meta.get(department, {})
#     return dept_meta.get("optional_metadata", _DEFAULT_OPTIONAL_METADATA)


# def get_document_type_metadata(department: str, document_type: str) -> list[str]:
#     dept_meta = _dept_meta.get(department, {})
#     doc_meta = dept_meta.get("document_type_metadata", {})
#     return doc_meta.get(document_type, [])


# # ── Enum helpers ───────────────────────────────────────────────────────────────

# def get_document_status_types(department: str) -> list[str]:
#     dept_meta = _dept_meta.get(department, {})
#     return dept_meta.get("status_types", _DEFAULT_STATUS_TYPES)


# def get_confidentiality_levels(department: str) -> list[str]:
#     dept_meta = _dept_meta.get(department, {})
#     return dept_meta.get("confidentiality_levels", _DEFAULT_CONFIDENTIALITY)


# def get_data_classification_types(department: str) -> list[str]:
#     dept_meta = _dept_meta.get(department, {})
#     return dept_meta.get("data_classification_types", _DEFAULT_DATA_CLASSIFICATION)


# # ── Full schema bundle ─────────────────────────────────────────────────────────

# def get_full_schema(department: str, document_type: str) -> dict:
#     """
#     Returns everything needed for the /schema endpoint in one call.
#     """
#     return {
#         "department":              department,
#         "document_type":           document_type,
#         "sections":                get_sections(department, document_type),
#         "required_metadata":       get_required_metadata(department),
#         "optional_metadata":       get_optional_metadata(department),
#         "doc_type_metadata":       get_document_type_metadata(department, document_type),
#         "questions":               get_all_questions(department, document_type),
#         "status_types":            get_document_status_types(department),
#         "confidentiality_levels":  get_confidentiality_levels(department),
#         "data_classification_types": get_data_classification_types(department),
#     }
#--------------------------------------------------------
# from pydantic import BaseModel, Field
# from typing import Dict, Any, Optional


# class DocumentGenerateRequest(BaseModel):
#     industry: str = Field(..., example="SaaS")
#     department: str = Field(..., example="HR & People Operations")
#     document_type: str = Field(..., example="SOP")
#     question_answers: Dict[str, Any] = Field(
#         ...,
#         example={
#             "company_name": "TechFlow Solutions",
#             "company_size": "51-200 (Medium)",
#             "purpose": "Define structured onboarding process",
#             "scope": "All new employees joining the company",
#             "tools_used": ["BambooHR", "Slack", "Zoom"],
#             "compliance_notes": "Must follow ISO 27001 guidelines",
#         },
#     )

#------------------------------------------------------------------------------

# from pydantic import BaseModel, Field
# from typing import Dict, Any, Optional


# class DocumentGenerateRequest(BaseModel):
#     industry: str = Field(..., example="SaaS")
#     department: str = Field(..., example="HR & People Operations")
#     document_type: str = Field(..., example="SOP")
#     question_answers: Dict[str, Any] = Field(
#         ...,
#         example={
#             "purpose": "Define structured onboarding process",
#             "scope": "All new employees joining the company",
#             "tools_used": "HRMS, Slack, Email",
#             "compliance_notes": "Must follow ISO 27001 guidelines",
#         },
#     )


# class TemplateCreateRequest(BaseModel):
#     document_type: str = Field(..., example="SOP")
#     department: str = Field(..., example="HR & People Operations")
#     structure: Dict[str, Any] = Field(
#         ...,
#         example={
#             "sections": [
#                 "Purpose",
#                 "Scope",
#                 "Roles & Responsibilities",
#                 "Process Steps",
#                 "Compliance Requirements",
#             ]
#         },
#     )


# class TemplateUpdateRequest(BaseModel):
#     structure: Dict[str, Any] = Field(
#         ...,
#         example={
#             "sections": [
#                 "Purpose",
#                 "Scope",
#                 "Updated Process Steps",
#                 "Compliance Requirements",
#             ]
#         },
#     )


# class QuestionnaireCreateRequest(BaseModel):
#     document_type: str = Field(..., example="SOP")
#     department: str = Field(..., example="HR & People Operations")
#     questions: list = Field(
#         ...,
#         example=[
#             {"key": "purpose", "label": "What is the purpose of this document?"},
#             {"key": "scope", "label": "Who does this document apply to?"},
#             {"key": "tools_used", "label": "What tools or systems are involved?"},
#         ],
#     )

# from pydantic import BaseModel
# from typing import Dict, Any


# class DocumentGenerateRequest(BaseModel):
#     document_type: str
#     department: str
#     metadata: Dict[str, Any]
#     user_responses: Dict[str, Any]


# class DocumentGenerateResponse(BaseModel):
#     status: str
#     document: str
