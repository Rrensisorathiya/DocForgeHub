from db import get_connection
import json
from fastapi import HTTPException


def create_template(payload: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO templates (document_type, department, structure)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (
            payload["document_type"],
            payload["department"],
            json.dumps(payload["structure"]),
        ),
    )

    template_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "created", "template_id": str(template_id)}


def list_templates():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, document_type, department, created_at FROM templates")
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "id": str(row[0]),
            "document_type": row[1],
            "department": row[2],
            "created_at": str(row[3]),
        }
        for row in results
    ]


def get_template(template_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, document_type, department, structure FROM templates WHERE id = %s",
        (template_id,),
    )
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "template_id": str(result[0]),
        "document_type": result[1],
        "department": result[2],
        "structure": result[3],
    }


def get_template_by_type(document_type: str):
    """Fetch template by document_type — used by document generator."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, document_type, department, structure FROM templates WHERE document_type = %s LIMIT 1",
        (document_type,),
    )
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if not result:
        return None

    return {
        "template_id": str(result[0]),
        "document_type": result[1],
        "department": result[2],
        "structure": result[3],
    }


def update_template(template_id: str, payload: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE templates
        SET structure = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (json.dumps(payload["structure"]), template_id),
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "updated"}


def delete_template(template_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM templates WHERE id = %s", (template_id,))

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "deleted"}
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
