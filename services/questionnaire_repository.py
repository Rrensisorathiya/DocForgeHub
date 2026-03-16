"""
services/questionnaire_repository.py
-------------------------------------
DB repository for the `questionnaires` table.

FIX: get_questionnaire_by_type() parameter order was inconsistent between
     callers and definition. Standardised to (department, document_type)
     to match how api/questionnaires.py calls it.
"""

from __future__ import annotations

import json
from fastapi import HTTPException
from db import get_connection
from utils.logger import setup_logger

logger = setup_logger(__name__)


def create_questionnaire(payload: dict) -> dict:
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO questionnaires (document_type, department, questions, version)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (department, document_type)
            DO UPDATE SET questions = EXCLUDED.questions,
                          updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """,
            (
                payload["document_type"],
                payload["department"],
                json.dumps(payload["questions"]),
                payload.get("version", "1.0"),
            ),
        )
        q_id = cursor.fetchone()[0]
        conn.commit()
        return {"status": "created", "questionnaire_id": str(q_id)}
    finally:
        cursor.close()
        conn.close()


def list_questionnaires() -> list[dict]:
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, document_type, department, version
            FROM questionnaires
            ORDER BY department, document_type
            """
        )
        rows = cursor.fetchall()
        return [
            {
                "id":            str(r[0]),
                "document_type": r[1],
                "department":    r[2],
                "version":       r[3],
            }
            for r in rows
        ]
    finally:
        cursor.close()
        conn.close()


def get_questionnaire(q_id: int | str) -> dict:
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, document_type, department, questions, version
            FROM questionnaires
            WHERE id = %s
            """,
            (q_id,),
        )
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Questionnaire not found")
        qs = r[3]
        if isinstance(qs, str):
            qs = json.loads(qs)
        return {
            "questionnaire_id": str(r[0]),
            "document_type":    r[1],
            "department":       r[2],
            "questions":        qs,
            "version":          r[4],
        }
    finally:
        cursor.close()
        conn.close()


def get_questionnaire_by_type(
    department: str,
    document_type: str,
) -> dict | None:
    """
    Fetch a questionnaire by (department, document_type).

    Returns None (not 404) if not found — callers fall back to JSON schema.

    NOTE: parameter order is (department, document_type) — matches every
    call-site in api/questionnaires.py.
    """
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, document_type, department, questions, version
            FROM questionnaires
            WHERE department = %s AND document_type = %s
            LIMIT 1
            """,
            (department, document_type),
        )
        r = cursor.fetchone()
        if not r:
            return None
        qs = r[3]
        if isinstance(qs, str):
            qs = json.loads(qs)
        return {
            "questionnaire_id": str(r[0]),
            "document_type":    r[1],
            "department":       r[2],
            "questions":        qs,
            "version":          r[4],
        }
    finally:
        cursor.close()
        conn.close()


def delete_questionnaire(q_id: int | str) -> dict:
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM questionnaires WHERE id = %s", (q_id,))
        conn.commit()
        return {"status": "deleted", "id": str(q_id)}
    finally:
        cursor.close()
        conn.close()


#---------------------------------------------------------------------------------

# """
# services/questionnaire_repository.py — matches new questionnaires table
# """
# from db import get_connection
# import json
# from fastapi import HTTPException


# def create_questionnaire(payload: dict):
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("""
#         INSERT INTO questionnaires (document_type, department, questions, version)
#         VALUES (%s, %s, %s, %s)
#         ON CONFLICT (department, document_type)
#         DO UPDATE SET questions = EXCLUDED.questions, updated_at = CURRENT_TIMESTAMP
#         RETURNING id
#     """, (
#         payload["document_type"],
#         payload["department"],
#         json.dumps(payload["questions"]),
#         payload.get("version", "1.0"),
#     ))
#     q_id = cursor.fetchone()[0]
#     conn.commit(); cursor.close(); conn.close()
#     return {"status": "created", "questionnaire_id": str(q_id)}


# def list_questionnaires():
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("SELECT id, document_type, department, version FROM questionnaires ORDER BY department, document_type")
#     results = cursor.fetchall()
#     cursor.close(); conn.close()
#     return [{"id": str(r[0]), "document_type": r[1], "department": r[2], "version": r[3]} for r in results]


# def get_questionnaire(q_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("SELECT id, document_type, department, questions FROM questionnaires WHERE id = %s", (q_id,))
#     r = cursor.fetchone()
#     cursor.close(); conn.close()
#     if not r: raise HTTPException(status_code=404, detail="Questionnaire not found")
#     return {"questionnaire_id": str(r[0]), "document_type": r[1], "department": r[2], "questions": r[3]}


# def get_questionnaire_by_type(document_type: str, department: str = None):
#     conn = get_connection()
#     cursor = conn.cursor()
#     if department:
#         cursor.execute("SELECT id, document_type, department, questions FROM questionnaires WHERE document_type = %s AND department = %s LIMIT 1", (document_type, department))
#     else:
#         cursor.execute("SELECT id, document_type, department, questions FROM questionnaires WHERE document_type = %s LIMIT 1", (document_type,))
#     r = cursor.fetchone()
#     cursor.close(); conn.close()
#     if not r: return None
#     return {"questionnaire_id": str(r[0]), "document_type": r[1], "department": r[2], "questions": r[3]}


# def delete_questionnaire(q_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("DELETE FROM questionnaires WHERE id = %s", (q_id,))
#     conn.commit(); cursor.close(); conn.close()
#     return {"status": "deleted"}

#-------------------------------------------------------------------------------

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

#     cursor.execute("SELECT id, document_type, department FROM questionnaires")
#     results = cursor.fetchall()

#     cursor.close()
#     conn.close()

#     return [
#         {
#             "id": str(row[0]),
#             "document_type": row[1],
#             "department": row[2],
#         }
#         for row in results
#     ]


# def get_questionnaire(q_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         "SELECT id, document_type, department, questions FROM questionnaires WHERE id = %s",
#         (q_id,),
#     )
#     result = cursor.fetchone()

#     cursor.close()
#     conn.close()

#     if not result:
#         raise HTTPException(status_code=404, detail="Questionnaire not found")

#     return {
#         "questionnaire_id": str(result[0]),
#         "document_type": result[1],
#         "department": result[2],
#         "questions": result[3],
#     }


# def get_questionnaire_by_type(document_type: str):
#     """Fetch questionnaire by document_type — used by document generator."""
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         "SELECT id, document_type, department, questions FROM questionnaires WHERE document_type = %s LIMIT 1",
#         (document_type,),
#     )
#     result = cursor.fetchone()

#     cursor.close()
#     conn.close()

#     if not result:
#         return None

#     return {
#         "questionnaire_id": str(result[0]),
#         "document_type": result[1],
#         "department": result[2],
#         "questions": result[3],
#     }


# def delete_questionnaire(q_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute("DELETE FROM questionnaires WHERE id = %s", (q_id,))

#     conn.commit()
#     cursor.close()
#     conn.close()

#     return {"status": "deleted"}

#-----------------------------------------------------------------------------------


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
