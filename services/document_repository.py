from db import get_connection
import json
from fastapi import HTTPException


def save_generated_document(
    industry: str,
    document_type: str,
    department: str,
    question_answers: dict,
    generated_content: str,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO generated_documents
            (document_type, department, industry, question_answers, generated_content)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            document_type,
            department,
            industry,
            json.dumps(question_answers),
            generated_content,
        ),
    )

    document_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    return str(document_id)


def list_documents(department: str = None, document_type: str = None, industry: str = None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, document_type, department, industry, created_at
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
    if industry:
        query += " AND industry = %s"
        params.append(industry)

    query += " ORDER BY created_at DESC"

    cursor.execute(query, tuple(params))
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "id": str(row[0]),
            "document_type": row[1],
            "department": row[2],
            "industry": row[3],
            "created_at": str(row[4]),
        }
        for row in results
    ]


def get_document(document_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, document_type, department, industry, question_answers, generated_content, created_at
        FROM generated_documents WHERE id = %s
        """,
        (document_id,),
    )
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": str(result[0]),
        "document_type": result[1],
        "department": result[2],
        "industry": result[3],
        "question_answers": result[4],
        "generated_content": result[5],
        "created_at": str(result[6]),
    }


def delete_document(document_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM generated_documents WHERE id = %s RETURNING id",
        (document_id,),
    )
    deleted = cursor.fetchone()

    conn.commit()
    cursor.close()
    conn.close()

    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"status": "deleted", "document_id": document_id}
# from db import get_connection
# import json
# from fastapi import HTTPException


# # ----------------------------------------
# # SAVE DOCUMENT
# # ----------------------------------------
# def save_generated_document(
#     document_type,
#     department,
#     metadata,
#     user_responses,
#     generated_content,
# ):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         """
#         INSERT INTO generated_documents
#         (document_type, department, metadata, user_responses, generated_content)
#         VALUES (%s, %s, %s, %s, %s)
#         RETURNING id
#         """,
#         (
#             document_type,
#             department,
#             json.dumps(metadata),
#             json.dumps(user_responses),
#             generated_content,
#         ),
#     )

#     document_id = cursor.fetchone()[0]

#     conn.commit()
#     cursor.close()
#     conn.close()

#     return str(document_id)


# # ----------------------------------------
# # LIST DOCUMENTS
# # ----------------------------------------
# def list_documents(department=None, document_type=None):
#     conn = get_connection()
#     cursor = conn.cursor()

#     query = """
#         SELECT id, document_type, department, created_at
#         FROM generated_documents
#         WHERE 1=1
#     """

#     params = []

#     if department:
#         query += " AND department = %s"
#         params.append(department)

#     if document_type:
#         query += " AND document_type = %s"
#         params.append(document_type)

#     cursor.execute(query, tuple(params))
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


# # ----------------------------------------
# # GET DOCUMENT
# # ----------------------------------------
# def get_document(document_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         "SELECT generated_content FROM generated_documents WHERE id = %s",
#         (document_id,),
#     )

#     result = cursor.fetchone()

#     cursor.close()
#     conn.close()

#     if not result:
#         raise HTTPException(status_code=404, detail="Document not found")

#     return {
#         "document_id": document_id,
#         "document": result[0],
#     }


# # ----------------------------------------
# # DELETE DOCUMENT
# # ----------------------------------------
# def delete_document(document_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         "DELETE FROM generated_documents WHERE id = %s",
#         (document_id,),
#     )

#     conn.commit()
#     cursor.close()
#     conn.close()

#     return {"status": "deleted"}
