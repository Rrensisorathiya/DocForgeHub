from fastapi import APIRouter, Query , HTTPException
from typing import Optional , List
from services.template_repository import list_templates, get_template
from db import get_connection
from utils.logger import setup_logger
import json
from pydantic import BaseModel
# from fastapi import APIRouter, Query, HTTPException
# from typing import Optional, List


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

class SectionUpdateRequest(BaseModel):
    sections: List[str]

@router.put("/{template_id}/sections", summary="Update sections of a template")
def update_sections(template_id: str, body: SectionUpdateRequest):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT structure FROM templates WHERE id = %s", (template_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="Template not found")
    
    structure = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    structure["sections"] = body.sections
    
    cur.execute(
        "UPDATE templates SET structure = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (json.dumps(structure), template_id)
    )
    conn.commit()
    cur.close(); conn.close()
    logger.info(f"Template {template_id} sections updated: {len(body.sections)} sections")
    return {"success": True, "template_id": template_id, "sections": body.sections}
