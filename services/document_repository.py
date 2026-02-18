from db import get_connection
import json
from fastapi import HTTPException


# ----------------------------------------
# SAVE DOCUMENT
# ----------------------------------------
def save_generated_document(
    document_type,
    department,
    metadata,
    user_responses,
    generated_content,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO generated_documents
        (document_type, department, metadata, user_responses, generated_content)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            document_type,
            department,
            json.dumps(metadata),
            json.dumps(user_responses),
            generated_content,
        ),
    )

    document_id = cursor.fetchone()[0]

    conn.commit()
    cursor.close()
    conn.close()

    return str(document_id)


# ----------------------------------------
# LIST DOCUMENTS
# ----------------------------------------
def list_documents(department=None, document_type=None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, document_type, department, created_at
        FROM generated_documents
        WHERE 1=1
    """

    params = []

    if department:
        query += " AND department = %s"
        params.append(department)

    if document_type:
        query += " AND document_type = %s"
        params.append(document_type)

    cursor.execute(query, tuple(params))
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "id": row[0],
            "document_type": row[1],
            "department": row[2],
            "created_at": row[3],
        }
        for row in results
    ]


# ----------------------------------------
# GET DOCUMENT
# ----------------------------------------
def get_document(document_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT generated_content FROM generated_documents WHERE id = %s",
        (document_id,),
    )

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": document_id,
        "document": result[0],
    }


# ----------------------------------------
# DELETE DOCUMENT
# ----------------------------------------
def delete_document(document_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM generated_documents WHERE id = %s",
        (document_id,),
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "deleted"}
