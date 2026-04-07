"""
Export API — registered at prefix /export in main.py
Routes: GET /export/{document_id}/docx
        GET /export/{document_id}/pdf
"""
import re
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


def _fname(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', str(text))


def _load_doc(document_id: str) -> dict:
    """Load document from DB, raise clean 404 if not found."""
    try:
        from services.document_repository import get_document
        doc = get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found: {e}")


@router.get("/{document_id}/docx", summary="Export as Word (.docx)")
def export_docx(document_id: str):
    logger.info(f"DOCX export requested for document: {document_id}")
    try:
        doc          = _load_doc(document_id)
        content      = doc.get("generated_content", "")
        doc_type     = doc.get("document_type", "Document")
        department   = doc.get("department", "")
        qa           = doc.get("question_answers") or {}
        company_name = qa.get("company_name", "") if isinstance(qa, dict) else ""

        if not content:
            logger.warning(f"Document {document_id} has no content to export")
            raise HTTPException(status_code=422, detail="Document has no content to export")

        logger.debug(f"Exporting {doc_type} from {department} department")
        try:
            from services.document_exporter import export_to_docx
            file_bytes = export_to_docx(content, doc_type, department, company_name)
            logger.info(f"DOCX export successful for document {document_id}")
        except Exception as e:
            logger.error(f"DOCX export failed for document {document_id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"DOCX export failed: {e}")

        fname = f"{_fname(doc_type)}_{_fname(department)}.docx"
        return Response(
            content=file_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during DOCX export for document {document_id}: {str(e)}", exc_info=True)
        raise


@router.get("/{document_id}/pdf", summary="Export as PDF")
def export_pdf(document_id: str):
    logger.info(f"PDF export requested for document: {document_id}")
    try:
        doc          = _load_doc(document_id)
        content      = doc.get("generated_content", "")
        doc_type     = doc.get("document_type", "Document")
        department   = doc.get("department", "")
        qa           = doc.get("question_answers") or {}
        company_name = qa.get("company_name", "") if isinstance(qa, dict) else ""

        if not content:
            logger.warning(f"Document {document_id} has no content to export")
            raise HTTPException(status_code=422, detail="Document has no content to export")

        logger.debug(f"Exporting {doc_type} from {department} department to PDF")
        try:
            from services.document_exporter import export_to_pdf
            file_bytes = export_to_pdf(content, doc_type, department, company_name)
            logger.info(f"PDF export successful for document {document_id}")
        except Exception as e:
            logger.error(f"PDF export failed for document {document_id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"PDF export failed: {e}")

        fname = f"{_fname(doc_type)}_{_fname(department)}.pdf"
        return Response(
            content=file_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during PDF export for document {document_id}: {str(e)}", exc_info=True)
        raise
