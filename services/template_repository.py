from db import get_connection
from fastapi import HTTPException
from utils.logger import setup_logger

logger = setup_logger(__name__)


def list_templates(department: str = None, document_type: str = None):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT id, department, document_type, version, is_active, created_at
        FROM templates WHERE 1=1
    """
    params = []
    if department:
        query += " AND department = %s"
        params.append(department)
    if document_type:
        query += " AND document_type = %s"
        params.append(document_type)
    query += " ORDER BY department, document_type"

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close(); conn.close()

    return [
        {
            "id": str(r[0]),
            "department": r[1],
            "document_type": r[2],
            "version": r[3],
            "is_active": r[4],
            "created_at": str(r[5]),
        }
        for r in rows
    ]


def get_template(template_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, department, document_type, structure, version, is_active FROM templates WHERE id = %s",
        (template_id,),
    )
    r = cur.fetchone()
    cur.close(); conn.close()

    if not r:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "id": str(r[0]),
        "department": r[1],
        "document_type": r[2],
        "structure": r[3],
        "version": r[4],
        "is_active": r[5],
    }


def get_template_by_type(document_type: str, department: str = None):
    conn = get_connection()
    cur = conn.cursor()

    if department:
        cur.execute(
            """SELECT id, department, document_type, structure
               FROM templates
               WHERE document_type = %s AND department = %s AND is_active = TRUE
               LIMIT 1""",
            (document_type, department),
        )
    else:
        cur.execute(
            """SELECT id, department, document_type, structure
               FROM templates
               WHERE document_type = %s AND is_active = TRUE
               LIMIT 1""",
            (document_type,),
        )

    r = cur.fetchone()
    cur.close(); conn.close()

    if not r:
        return None

    return {
        "template_id": str(r[0]),
        "department": r[1],
        "document_type": r[2],
        "structure": r[3],
    }
