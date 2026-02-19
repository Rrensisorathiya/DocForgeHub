# # api/documents.py

# from fastapi import APIRouter, HTTPException
# from schemas.document_schema import DocumentGenerateRequest, DocumentGenerateResponse
# from services.document_generator import generate_document

# router = APIRouter()


# @router.post("/generate", response_model=DocumentGenerateResponse)
# def generate_document_endpoint(request: DocumentGenerateRequest):
#     try:
#         template_json = {
#             "sections": [
#                 "Purpose",
#                 "Scope",
#                 "Roles & Responsibilities",
#                 "Process Steps",
#                 "Compliance Requirements"
#             ]
#         }

#         document = generate_document(
#             document_type=request.document_type,
#             department=request.department,
#             template_json=template_json,
#             metadata=request.metadata,
#             user_responses=request.user_responses,
#         )

#         return DocumentGenerateResponse(
#             status="success",
#             document=document
#         )

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
# from fastapi import APIRouter
# from schemas.document_schema import DocumentGenerateRequest
# from services.document_generator import generate_document
# from services.document_repository import (
#     save_generated_document,
#     list_documents,
#     get_document,
#     delete_document,
# )

# router = APIRouter()

# @router.post("/generate")
# def generate(request: DocumentGenerateRequest):

#     template_json = {
#         "sections": [
#             "Purpose",
#             "Scope",
#             "Roles & Responsibilities",
#             "Process Steps",
#             "Compliance Requirements"
#         ]
#     }

#     document = generate_document(
#         document_type=request.document_type,
#         department=request.department,
#         template_json=template_json,
#         metadata=request.metadata,
#         user_responses=request.user_responses,
#     )

#     document_id = save_generated_document(
#         request.document_type,
#         request.department,
#         request.metadata,
#         request.user_responses,
#         document,
#     )

#     return {
#         "status": "success",
#         "document_id": document_id,
#         "document": document,
#     }

# @router.get("/")
# def list_all(department: str = None, document_type: str = None):
#     return list_documents(department, document_type)

# @router.get("/{document_id}")
# def get_one(document_id: str):
#     return get_document(document_id)

# @router.delete("/{document_id}")
# def delete_one(document_id: str):
#     return delete_document(document_id)
from fastapi import APIRouter, Query
from typing import Optional
from schemas.document_schema import DocumentGenerateRequest
from services.document_generator import generate_document
from services.document_repository import (
    save_generated_document,
    list_documents,
    get_document,
    delete_document,
)

router = APIRouter()


@router.post("/generate", summary="Generate a new document using AI")
def generate(request: DocumentGenerateRequest):
    """
    Generate a full document using the AI engine.

    **Flow:**
    1. Fetch matching template by `document_type`
    2. Extract sections from template structure
    3. Generate each section via Azure OpenAI
    4. Save the final document to DB
    5. Return document content + ID
    """

    document = generate_document(
        industry=request.industry,
        department=request.department,
        document_type=request.document_type,
        question_answers=request.question_answers,
    )

    document_id = save_generated_document(
        industry=request.industry,
        document_type=request.document_type,
        department=request.department,
        question_answers=request.question_answers,
        generated_content=document,
    )

    return {
        "status": "success",
        "document_id": document_id,
        "document": document,
    }


@router.get("/", summary="List all generated documents")
def list_all(
    department: Optional[str] = Query(None, description="Filter by department"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
):
    return list_documents(department=department, document_type=document_type, industry=industry)


@router.get("/{document_id}", summary="Get a single document by ID")
def get_one(document_id: str):
    return get_document(document_id)


@router.delete("/{document_id}", summary="Delete a document by ID")
def delete_one(document_id: str):
    return delete_document(document_id)