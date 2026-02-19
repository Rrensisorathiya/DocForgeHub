from db import get_connection
import json
from fastapi import HTTPException


def create_questionnaire(payload: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO questionnaires (document_type, department, questions)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (
            payload["document_type"],
            payload["department"],
            json.dumps(payload["questions"]),
        ),
    )

    q_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "created", "questionnaire_id": str(q_id)}


def list_questionnaires():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, document_type, department FROM questionnaires")
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "id": str(row[0]),
            "document_type": row[1],
            "department": row[2],
        }
        for row in results
    ]


def get_questionnaire(q_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, document_type, department, questions FROM questionnaires WHERE id = %s",
        (q_id,),
    )
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Questionnaire not found")

    return {
        "questionnaire_id": str(result[0]),
        "document_type": result[1],
        "department": result[2],
        "questions": result[3],
    }


def get_questionnaire_by_type(document_type: str):
    """Fetch questionnaire by document_type — used by document generator."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, document_type, department, questions FROM questionnaires WHERE document_type = %s LIMIT 1",
        (document_type,),
    )
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if not result:
        return None

    return {
        "questionnaire_id": str(result[0]),
        "document_type": result[1],
        "department": result[2],
        "questions": result[3],
    }


def delete_questionnaire(q_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM questionnaires WHERE id = %s", (q_id,))

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "deleted"}
# from db import get_connection
# import json
# from fastapi import HTTPException


# def create_questionnaire(payload: dict):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         """
#         INSERT INTO questionnaires (document_type, department, questions)
#         VALUES (%s, %s, %s)
#         RETURNING id
#         """,
#         (
#             payload["document_type"],
#             payload["department"],
#             json.dumps(payload["questions"]),
#         ),
#     )

#     q_id = cursor.fetchone()[0]

#     conn.commit()
#     cursor.close()
#     conn.close()

#     return {"status": "created", "questionnaire_id": str(q_id)}


# def list_questionnaires():
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         "SELECT id, document_type, department FROM questionnaires"
#     )

#     results = cursor.fetchall()

#     cursor.close()
#     conn.close()

#     return [
#         {
#             "id": row[0],
#             "document_type": row[1],
#             "department": row[2],
#         }
#         for row in results
#     ]


# def get_questionnaire(q_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         "SELECT questions FROM questionnaires WHERE id = %s",
#         (q_id,),
#     )

#     result = cursor.fetchone()

#     cursor.close()
#     conn.close()

#     if not result:
#         raise HTTPException(status_code=404, detail="Questionnaire not found")

#     return {
#         "questionnaire_id": q_id,
#         "questions": result[0],
#     }


# def delete_questionnaire(q_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         "DELETE FROM questionnaires WHERE id = %s",
#         (q_id,),
#     )

#     conn.commit()
#     cursor.close()
#     conn.close()

#     return {"status": "deleted"}
