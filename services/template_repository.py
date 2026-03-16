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
# """
# services/template_repository.py — matches new templates table
# """
# from db import get_connection
# import json
# from fastapi import HTTPException


# def create_template(payload: dict):
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("""
#         INSERT INTO templates (department, document_type, structure, version)
#         VALUES (%s, %s, %s, %s)
#         ON CONFLICT (department, document_type)
#         DO UPDATE SET structure = EXCLUDED.structure, updated_at = CURRENT_TIMESTAMP
#         RETURNING id
#     """, (
#         payload["department"],
#         payload["document_type"],
#         json.dumps(payload["structure"]),
#         payload.get("version", "1.0"),
#     ))
#     template_id = cursor.fetchone()[0]
#     conn.commit(); cursor.close(); conn.close()
#     return {"status": "created", "template_id": str(template_id)}


# def list_templates():
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("SELECT id, department, document_type, version, is_active, created_at FROM templates ORDER BY department, document_type")
#     results = cursor.fetchall()
#     cursor.close(); conn.close()
#     return [{"id": str(r[0]), "department": r[1], "document_type": r[2], "version": r[3], "is_active": r[4], "created_at": str(r[5])} for r in results]


# def get_template(template_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("SELECT id, department, document_type, structure, version FROM templates WHERE id = %s", (template_id,))
#     r = cursor.fetchone()
#     cursor.close(); conn.close()
#     if not r: raise HTTPException(status_code=404, detail="Template not found")
#     return {"template_id": str(r[0]), "department": r[1], "document_type": r[2], "structure": r[3], "version": r[4]}


# def get_template_by_type(document_type: str, department: str = None):
#     conn = get_connection()
#     cursor = conn.cursor()
#     if department:
#         cursor.execute("SELECT id, department, document_type, structure FROM templates WHERE document_type = %s AND department = %s AND is_active = TRUE LIMIT 1", (document_type, department))
#     else:
#         cursor.execute("SELECT id, department, document_type, structure FROM templates WHERE document_type = %s AND is_active = TRUE LIMIT 1", (document_type,))
#     r = cursor.fetchone()
#     cursor.close(); conn.close()
#     if not r: return None
#     return {"template_id": str(r[0]), "department": r[1], "document_type": r[2], "structure": r[3]}


# def update_template(template_id: str, payload: dict):
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("UPDATE templates SET structure = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (json.dumps(payload["structure"]), template_id))
#     conn.commit(); cursor.close(); conn.close()
#     return {"status": "updated"}


# def delete_template(template_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("DELETE FROM templates WHERE id = %s", (template_id,))
#     conn.commit(); cursor.close(); conn.close()
#     return {"status": "deleted"}

#--------------------------------------------------------------------------------

# from db import get_connection
# import json
# from fastapi import HTTPException


# def create_template(payload: dict):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         """
#         INSERT INTO templates (document_type, department, structure)
#         VALUES (%s, %s, %s)
#         RETURNING id
#         """,
#         (
#             payload["document_type"],
#             payload["department"],
#             json.dumps(payload["structure"]),
#         ),
#     )

#     template_id = cursor.fetchone()[0]
#     conn.commit()
#     cursor.close()
#     conn.close()

#     return {"status": "created", "template_id": str(template_id)}


# def list_templates():
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute("SELECT id, document_type, department, created_at FROM templates")
#     results = cursor.fetchall()

#     cursor.close()
#     conn.close()

#     return [
#         {
#             "id": str(row[0]),
#             "document_type": row[1],
#             "department": row[2],
#             "created_at": str(row[3]),
#         }
#         for row in results
#     ]


# def get_template(template_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         "SELECT id, document_type, department, structure FROM templates WHERE id = %s",
#         (template_id,),
#     )
#     result = cursor.fetchone()

#     cursor.close()
#     conn.close()

#     if not result:
#         raise HTTPException(status_code=404, detail="Template not found")

#     return {
#         "template_id": str(result[0]),
#         "document_type": result[1],
#         "department": result[2],
#         "structure": result[3],
#     }


# def get_template_by_type(document_type: str):
#     """Fetch template by document_type — used by document generator."""
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         "SELECT id, document_type, department, structure FROM templates WHERE document_type = %s LIMIT 1",
#         (document_type,),
#     )
#     result = cursor.fetchone()

#     cursor.close()
#     conn.close()

#     if not result:
#         return None

#     return {
#         "template_id": str(result[0]),
#         "document_type": result[1],
#         "department": result[2],
#         "structure": result[3],
#     }


# def update_template(template_id: str, payload: dict):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         """
#         UPDATE templates
#         SET structure = %s, updated_at = CURRENT_TIMESTAMP
#         WHERE id = %s
#         """,
#         (json.dumps(payload["structure"]), template_id),
#     )

#     conn.commit()
#     cursor.close()
#     conn.close()

#     return {"status": "updated"}


# def delete_template(template_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute("DELETE FROM templates WHERE id = %s", (template_id,))

#     conn.commit()
#     cursor.close()
#     conn.close()

#     return {"status": "deleted"}
#-------------------------------------------------------------------------------------------
# from db import get_connection
# import json
# from fastapi import HTTPException


# def create_template(payload: dict):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         """
#         INSERT INTO templates (document_type, department, template_structure)
#         VALUES (%s, %s, %s)
#         RETURNING id
#         """,
#         (
#             payload["document_type"],
#             payload["department"],
#             json.dumps(payload["template_structure"]),
#         ),
#     )

#     template_id = cursor.fetchone()[0]

#     conn.commit()
#     cursor.close()
#     conn.close()

#     return {"status": "created", "template_id": str(template_id)}


# def list_templates():
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         "SELECT id, document_type, department, created_at FROM templates"
#     )

#     results = cursor.fetchall()

#     cursor.close()
#     conn.close()

#     return [
#         {
#             "id": row[0],
#             "document_type": row[1],
#             "department": row[2],
#             "created_at": row[3],
#         }
#         for row in results
#     ]


# def get_template(template_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         "SELECT template_structure FROM templates WHERE id = %s",
#         (template_id,),
#     )

#     result = cursor.fetchone()

#     cursor.close()
#     conn.close()

#     if not result:
#         raise HTTPException(status_code=404, detail="Template not found")

#     return {
#         "template_id": template_id,
#         "template_structure": result[0],
#     }


# def update_template(template_id: str, payload: dict):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         """
#         UPDATE templates
#         SET template_structure = %s,
#             updated_at = CURRENT_TIMESTAMP
#         WHERE id = %s
#         """,
#         (json.dumps(payload["template_structure"]), template_id),
#     )

#     conn.commit()
#     cursor.close()
#     conn.close()

#     return {"status": "updated"}


# def delete_template(template_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         "DELETE FROM templates WHERE id = %s",
#         (template_id,),
#     )

#     conn.commit()
#     cursor.close()
#     conn.close()

#     return {"status": "deleted"}
