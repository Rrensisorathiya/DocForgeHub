import uuid
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response
from fastapi.concurrency import run_in_threadpool
from typing import Optional
import re

from schemas.document_schema import DocumentGenerateRequest
from utils.logger import setup_logger

logger = setup_logger(__name__)
from services.document_generator import generate_document
from services.document_validator import validate_document
from services.document_repository import (
    create_job, fail_job, get_job_status, list_jobs,
    save_generated_document, list_documents, get_document, delete_document,
)

router = APIRouter()


# ══════════════════════════════════════
# STATIC ROUTES  (before any /{param})
# ══════════════════════════════════════

@router.post("/generate")
async def generate(request: DocumentGenerateRequest):
    job_id = str(uuid.uuid4())
    logger.info(f"Document generation started - Job ID: {job_id}, Type: {request.document_type}, Department: {request.department}")
    
    create_job(job_id=job_id, document_type=request.document_type,
               department=request.department, industry=request.industry,
               question_answers=request.question_answers)
    try:
        logger.debug(f"Starting document generation for job {job_id}")
        document = await run_in_threadpool(
            generate_document,
            industry=request.industry, department=request.department,
            document_type=request.document_type, question_answers=request.question_answers,
        )
        logger.debug(f"Document generated successfully for job {job_id}, saving to database")
        
        document_id, validation = await run_in_threadpool(
            save_generated_document,
            job_id=job_id, industry=request.industry, document_type=request.document_type,
            department=request.department, question_answers=request.question_answers,
            generated_content=document,
        )
        
        logger.info(f"Document saved successfully - Document ID: {document_id}, Job ID: {job_id}, Validation Score: {validation.get('score')}")
        return {
            "status": "success", "job_id": job_id,
            "document_id": document_id, "document": document,
            "validation": {
                "score":      validation.get("score"),
                "grade":      validation.get("grade"),
                "label":      validation.get("label"),
                "word_count": validation.get("word_count"),
                "valid":      validation.get("valid"),
                "summary":    validation.get("summary"),
                "passed":     validation.get("passed", []),
                "warnings":   validation.get("warnings", []),
                "issues":     validation.get("issues", []),
            },
        }
    except Exception as e:
        logger.error(f"Document generation failed for job {job_id}: {str(e)}", exc_info=True)
        fail_job(job_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
def all_jobs(status: Optional[str] = Query(None)):
    logger.debug(f"Fetching all jobs with status filter: {status}")
    result = list_jobs(status=status)
    logger.debug(f"Retrieved {len(result) if isinstance(result, list) else 'unknown number of'} jobs")
    return result


@router.get("/")
def list_all(
    department:    Optional[str] = Query(None),
    document_type: Optional[str] = Query(None),
    industry:      Optional[str] = Query(None),
):
    logger.debug(f"Listing documents - Filters: department={department}, type={document_type}, industry={industry}")
    result = list_documents(department=department, document_type=document_type, industry=industry)
    logger.debug(f"Retrieved {len(result) if isinstance(result, list) else 'unknown number of'} documents")
    return result


@router.get("/job/{job_id}")
def check_job(job_id: str):
    logger.debug(f"Checking job status for job ID: {job_id}")
    return get_job_status(job_id)


# ══════════════════════════════════════
# DYNAMIC ROUTES  (/{id} — must be LAST)
# ══════════════════════════════════════

@router.get("/{document_id}/validate")
def validate_existing(document_id: str):
    logger.info(f"Validating document: {document_id}")
    try:
        doc = get_document(document_id)
        result = validate_document(
            content=doc.get("generated_content", ""),
            doc_type=doc.get("document_type", ""),
            department=doc.get("department", ""),
            question_answers=doc.get("question_answers", {}),
        )
        logger.debug(f"Validation complete for document {document_id} - Score: {result.get('score')}")
        return {"document_id": document_id, **result}
    except Exception as e:
        logger.error(f"Validation failed for document {document_id}: {str(e)}", exc_info=True)
        raise


@router.get("/{document_id}")
def get_one(document_id: str):
    logger.debug(f"Retrieving document: {document_id}")
    return get_document(document_id)


@router.delete("/{document_id}")
def delete_one(document_id: str):
    return delete_document(document_id)
# import uuid
# from fastapi import APIRouter, Query, HTTPException
# from typing import Optional
# from schemas.document_schema import DocumentGenerateRequest
# from services.document_generator import generate_document
# from services.document_repository import (
#     create_job, fail_job, get_job_status, list_jobs,
#     save_generated_document, list_documents, get_document, delete_document,
# )

# router = APIRouter()


# # ── STATIC ROUTES FIRST (before any /{param} routes) ──────────────────────

# @router.post("/generate", summary="Generate a new AI document")
# def generate(request: DocumentGenerateRequest):
#     job_id = str(uuid.uuid4())

#     create_job(
#         job_id=job_id,
#         document_type=request.document_type,
#         department=request.department,
#         industry=request.industry,
#         question_answers=request.question_answers,
#     )

#     try:
#         document = generate_document(
#             industry=request.industry,
#             department=request.department,
#             document_type=request.document_type,
#             question_answers=request.question_answers,
#         )

#         document_id = save_generated_document(
#             job_id=job_id,
#             industry=request.industry,
#             document_type=request.document_type,
#             department=request.department,
#             question_answers=request.question_answers,
#             generated_content=document,
#         )

#         return {
#             "status": "success",
#             "job_id": job_id,
#             "document_id": document_id,
#             "document": document,
#         }

#     except Exception as e:
#         fail_job(job_id, str(e))
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/jobs", summary="List all generation jobs")
# def all_jobs(
#     status: Optional[str] = Query(None, description="Filter: pending / processing / completed / failed")
# ):
#     return list_jobs(status=status)


# @router.get("/", summary="List all generated documents")
# def list_all(
#     department: Optional[str] = Query(None),
#     document_type: Optional[str] = Query(None),
#     industry: Optional[str] = Query(None),
# ):
#     return list_documents(department=department, document_type=document_type, industry=industry)


# # ── DYNAMIC ROUTES LAST (/{param} must come after all static routes) ───────

# @router.get("/job/{job_id}", summary="Check generation job status")
# def check_job(job_id: str):
#     return get_job_status(job_id)


# @router.get("/{document_id}", summary="Get a document by ID")
# def get_one(document_id: str):
#     return get_document(document_id)


# @router.delete("/{document_id}", summary="Delete a document by ID")
# def delete_one(document_id: str):
#     return delete_document(document_id)

#-----------------------------------------------------------------------------------
# import uuid
# from fastapi import APIRouter, Query
# from typing import Optional
# from schemas.document_schema import DocumentGenerateRequest
# from services.document_generator import generate_document
# from services.document_repository import (
#     create_job, fail_job, get_job_status, list_jobs,
#     save_generated_document, list_documents, get_document, delete_document,
# )

# router = APIRouter()


# @router.post("/generate", summary="Generate a new AI document")
# def generate(request: DocumentGenerateRequest):
#     job_id = str(uuid.uuid4())

#     create_job(
#         job_id=job_id,
#         document_type=request.document_type,
#         department=request.department,
#         industry=request.industry,
#         question_answers=request.question_answers,
#     )

#     try:
#         document = generate_document(
#             industry=request.industry,
#             department=request.department,
#             document_type=request.document_type,
#             question_answers=request.question_answers,
#         )

#         document_id = save_generated_document(
#             job_id=job_id,
#             industry=request.industry,
#             document_type=request.document_type,
#             department=request.department,
#             question_answers=request.question_answers,
#             generated_content=document,
#         )

#         return {
#             "status": "success",
#             "job_id": job_id,
#             "document_id": document_id,
#             "document": document,
#         }

#     except Exception as e:
#         fail_job(job_id, str(e))
#         raise


# @router.get("/job/{job_id}", summary="Check generation job status")
# def check_job(job_id: str):
#     return get_job_status(job_id)


# @router.get("/jobs", summary="List all generation jobs")
# def all_jobs(status: Optional[str] = Query(None, description="Filter: pending / processing / completed / failed")):
#     return list_jobs(status=status)


# @router.get("/", summary="List all generated documents")
# def list_all(
#     department: Optional[str] = Query(None),
#     document_type: Optional[str] = Query(None),
#     industry: Optional[str] = Query(None),
# ):
#     return list_documents(department=department, document_type=document_type, industry=industry)


# @router.get("/{document_id}", summary="Get a document by ID")
# def get_one(document_id: str):
#     return get_document(document_id)


# @router.delete("/{document_id}", summary="Delete a document by ID")
# def delete_one(document_id: str):
#     return delete_document(document_id)

#-------------------------------------------------------------------------------------------

# import uuid
# from fastapi import APIRouter, Query
# from typing import Optional
# from schemas.document_schema import DocumentGenerateRequest
# from services.document_generator import generate_document
# from services.document_repository import (
#     save_generated_document,
#     create_job,
#     fail_job,
#     get_job_status,
#     list_documents,
#     get_document,
#     delete_document,
# )

# router = APIRouter()


# @router.post("/generate", summary="Generate a new AI document")
# def generate(request: DocumentGenerateRequest):
#     job_id = str(uuid.uuid4())

#     # Create job record
#     create_job(
#         job_id=job_id,
#         document_type=request.document_type,
#         department=request.department,
#         industry=request.industry,
#         question_answers=request.question_answers,
#     )

#     try:
#         document = generate_document(
#             industry=request.industry,
#             department=request.department,
#             document_type=request.document_type,
#             question_answers=request.question_answers,
#         )

#         document_id = save_generated_document(
#             job_id=job_id,
#             industry=request.industry,
#             document_type=request.document_type,
#             department=request.department,
#             question_answers=request.question_answers,
#             generated_content=document,
#         )

#         return {
#             "status": "success",
#             "job_id": job_id,
#             "document_id": document_id,
#             "document": document,
#         }

#     except Exception as e:
#         fail_job(job_id, str(e))
#         raise


# @router.get("/job/{job_id}", summary="Check generation job status")
# def check_job(job_id: str):
#     return get_job_status(job_id)


# @router.get("/", summary="List all generated documents")
# def list_all(
#     department: Optional[str] = Query(None),
#     document_type: Optional[str] = Query(None),
#     industry: Optional[str] = Query(None),
# ):
#     return list_documents(department=department, document_type=document_type, industry=industry)


# @router.get("/{document_id}", summary="Get a document by ID")
# def get_one(document_id: str):
#     return get_document(document_id)


# @router.delete("/{document_id}", summary="Delete a document")
# def delete_one(document_id: str):
#     return delete_document(document_id)
# #-------------------------------------------------------------------------------------------

# from fastapi import APIRouter, Query
# from typing import Optional
# from schemas.document_schema import DocumentGenerateRequest
# from services.document_generator import generate_document
# from services.document_repository import (
#     save_generated_document,
#     list_documents,
#     get_document,
#     delete_document,
# )

# router = APIRouter()


# @router.post("/generate", summary="Generate a new document using AI")
# def generate(request: DocumentGenerateRequest):
#     """
#     Generate a full document using the AI engine.

#     **Flow:**
#     1. Fetch matching template by `document_type`
#     2. Extract sections from template structure
#     3. Generate each section via Azure OpenAI
#     4. Save the final document to DB
#     5. Return document content + ID
#     """

#     document = generate_document(
#         industry=request.industry,
#         department=request.department,
#         document_type=request.document_type,
#         question_answers=request.question_answers,
#     )

#     document_id = save_generated_document(
#         industry=request.industry,
#         document_type=request.document_type,
#         department=request.department,
#         question_answers=request.question_answers,
#         generated_content=document,
#     )

#     return {
#         "status": "success",
#         "document_id": document_id,
#         "document": document,
#     }


# @router.get("/", summary="List all generated documents")
# def list_all(
#     department: Optional[str] = Query(None, description="Filter by department"),
#     document_type: Optional[str] = Query(None, description="Filter by document type"),
#     industry: Optional[str] = Query(None, description="Filter by industry"),
# ):
#     return list_documents(department=department, document_type=document_type, industry=industry)


# @router.get("/{document_id}", summary="Get a single document by ID")
# def get_one(document_id: str):
#     return get_document(document_id)


# @router.delete("/{document_id}", summary="Delete a document by ID")
# def delete_one(document_id: str):
#     return delete_document(document_id)
#--------------------------------------------------------------------

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
