from fastapi import APIRouter, Query
from typing import Optional
from services.template_repository import list_templates, get_template
from db import get_connection
from utils.logger import setup_logger

logger = setup_logger(__name__)
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
