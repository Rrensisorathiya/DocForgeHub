from db import get_connection
from fastapi import HTTPException
import json


def create_job(job_id: str, document_type: str, department: str, industry: str, question_answers: dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO generation_jobs
           (job_id, status, document_type, department, industry, question_answers)
           VALUES (%s, 'processing', %s, %s, %s, %s)
           ON CONFLICT (job_id) DO NOTHING""",
        (job_id, document_type, department, industry, json.dumps(question_answers)),
    )
    conn.commit(); cur.close(); conn.close()


def fail_job(job_id: str, error: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """UPDATE generation_jobs
           SET status = 'failed', error_message = %s, completed_at = CURRENT_TIMESTAMP
           WHERE job_id = %s""",
        (error, job_id),
    )
    conn.commit(); cur.close(); conn.close()


def get_job_status(job_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT job_id, status, document_type, department, industry,
                  result_doc_id, error_message, started_at, completed_at
           FROM generation_jobs WHERE job_id = %s""",
        (job_id,),
    )
    r = cur.fetchone()
    cur.close(); conn.close()

    if not r:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": r[0],
        "status": r[1],
        "document_type": r[2],
        "department": r[3],
        "industry": r[4],
        "result_doc_id": r[5],
        "error_message": r[6],
        "started_at": str(r[7]),
        "completed_at": str(r[8]) if r[8] else None,
    }


def save_generated_document(
    job_id: str,
    industry: str,
    document_type: str,
    department: str,
    question_answers: dict,
    generated_content: str,
    template_id: int = None,
):
    # Run validation before saving
    try:
        from services.document_validator import validate_document
        validation = validate_document(
            content=generated_content,
            doc_type=document_type,
            department=department,
            question_answers=question_answers,
        )
    except Exception:
        validation = {"score": 0, "grade": "N/A", "valid": True, "word_count": len(generated_content.split())}

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """INSERT INTO generated_documents
           (job_id, document_type, department, industry, question_answers,
            generated_content, status, template_id)
           VALUES (%s, %s, %s, %s, %s, %s, 'completed', %s)
           RETURNING id""",
        (job_id, document_type, department, industry,
         json.dumps(question_answers), generated_content, template_id),
    )
    doc_id = cur.fetchone()[0]

    word_count   = validation.get("word_count", len(generated_content.split()))
    reading_time = max(1, word_count // 200)
    cur.execute(
        """INSERT INTO document_metadata
           (document_id, document_type, department, industry,
            word_count, reading_time, template_id, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, 'Draft')
           RETURNING id""",
        (str(doc_id), document_type, department, industry,
         word_count, reading_time, template_id),
    )
    meta_id = cur.fetchone()[0]

    cur.execute(
        "UPDATE generated_documents SET metadata_id = %s WHERE id = %s",
        (meta_id, doc_id),
    )

    changed_by = f"AI Generator | Score: {validation.get('score',0)}/100 | Grade: {validation.get('grade','N/A')}"
    cur.execute(
        """INSERT INTO document_versions
           (document_id, version, content, changed_by)
           VALUES (%s, '1.0', %s, %s)""",
        (doc_id, generated_content, changed_by),
    )

    cur.execute(
        """UPDATE generation_jobs
           SET status = 'completed', result_doc_id = %s, completed_at = CURRENT_TIMESTAMP
           WHERE job_id = %s""",
        (doc_id, job_id),
    )

    conn.commit(); cur.close(); conn.close()
    return str(doc_id), validation


def list_documents(department: str = None, document_type: str = None, industry: str = None):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT id, job_id, document_type, department, industry, status, created_at
        FROM generated_documents WHERE 1=1
    """
    params = []
    if department:
        query += " AND department = %s"; params.append(department)
    if document_type:
        query += " AND document_type = %s"; params.append(document_type)
    if industry:
        query += " AND industry = %s"; params.append(industry)
    query += " ORDER BY created_at DESC"

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close(); conn.close()

    return [
        {
            "id": str(r[0]),
            "job_id": r[1],
            "document_type": r[2],
            "department": r[3],
            "industry": r[4],
            "status": r[5],
            "created_at": str(r[6]),
        }
        for r in rows
    ]


def get_document(document_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT gd.id, gd.job_id, gd.document_type, gd.department, gd.industry,
                  gd.question_answers, gd.generated_content, gd.status, gd.created_at,
                  dm.word_count, dm.reading_time, dm.status as doc_status,
                  dm.tags, dm.compliance_tags, dm.priority, dm.confidentiality
           FROM generated_documents gd
           LEFT JOIN document_metadata dm ON dm.document_id = gd.id::text
           WHERE gd.id = %s""",
        (document_id,),
    )
    r = cur.fetchone()
    cur.close(); conn.close()

    if not r:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": str(r[0]),
        "job_id": r[1],
        "document_type": r[2],
        "department": r[3],
        "industry": r[4],
        "question_answers": r[5],
        "generated_content": r[6],
        "status": r[7],
        "created_at": str(r[8]),
        "metadata": {
            "word_count": r[9],
            "reading_time_minutes": r[10],
            "doc_status": r[11],
            "tags": r[12],
            "compliance_tags": r[13],
            "priority": r[14],
            "confidentiality": r[15],
        },
    }


def delete_document(document_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM document_metadata WHERE document_id = %s", (document_id,))
    cur.execute("DELETE FROM document_versions WHERE document_id = %s", (document_id,))
    cur.execute(
        "DELETE FROM generated_documents WHERE id = %s RETURNING id", (document_id,)
    )
    deleted = cur.fetchone()
    conn.commit(); cur.close(); conn.close()

    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"status": "deleted", "document_id": document_id}


def list_jobs(status: str = None):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT job_id, status, document_type, department, industry,
               result_doc_id, error_message, started_at, completed_at
        FROM generation_jobs WHERE 1=1
    """
    params = []
    if status:
        query += " AND status = %s"; params.append(status)
    query += " ORDER BY started_at DESC"

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close(); conn.close()

    return [
        {
            "job_id": r[0],
            "status": r[1],
            "document_type": r[2],
            "department": r[3],
            "industry": r[4],
            "result_doc_id": r[5],
            "error_message": r[6],
            "started_at": str(r[7]),
            "completed_at": str(r[8]) if r[8] else None,
        }
        for r in rows
    ]
# from db import get_connection
# from fastapi import HTTPException
# import json


# def create_job(job_id: str, document_type: str, department: str, industry: str, question_answers: dict):
#     conn = get_connection()
#     cur = conn.cursor()
#     cur.execute(
#         """INSERT INTO generation_jobs
#            (job_id, status, document_type, department, industry, question_answers)
#            VALUES (%s, 'processing', %s, %s, %s, %s)
#            ON CONFLICT (job_id) DO NOTHING""",
#         (job_id, document_type, department, industry, json.dumps(question_answers)),
#     )
#     conn.commit(); cur.close(); conn.close()


# def fail_job(job_id: str, error: str):
#     conn = get_connection()
#     cur = conn.cursor()
#     cur.execute(
#         """UPDATE generation_jobs
#            SET status = 'failed', error_message = %s, completed_at = CURRENT_TIMESTAMP
#            WHERE job_id = %s""",
#         (error, job_id),
#     )
#     conn.commit(); cur.close(); conn.close()


# def get_job_status(job_id: str):
#     conn = get_connection()
#     cur = conn.cursor()
#     cur.execute(
#         """SELECT job_id, status, document_type, department, industry,
#                   result_doc_id, error_message, started_at, completed_at
#            FROM generation_jobs WHERE job_id = %s""",
#         (job_id,),
#     )
#     r = cur.fetchone()
#     cur.close(); conn.close()

#     if not r:
#         raise HTTPException(status_code=404, detail="Job not found")

#     return {
#         "job_id": r[0],
#         "status": r[1],
#         "document_type": r[2],
#         "department": r[3],
#         "industry": r[4],
#         "result_doc_id": r[5],
#         "error_message": r[6],
#         "started_at": str(r[7]),
#         "completed_at": str(r[8]) if r[8] else None,
#     }


# def save_generated_document(
#     job_id: str,
#     industry: str,
#     document_type: str,
#     department: str,
#     question_answers: dict,
#     generated_content: str,
#     template_id: int = None,
# ):
#     conn = get_connection()
#     cur = conn.cursor()

#     # Save document
#     cur.execute(
#         """INSERT INTO generated_documents
#            (job_id, document_type, department, industry, question_answers,
#             generated_content, status, template_id)
#            VALUES (%s, %s, %s, %s, %s, %s, 'completed', %s)
#            RETURNING id""",
#         (job_id, document_type, department, industry,
#          json.dumps(question_answers), generated_content, template_id),
#     )
#     doc_id = cur.fetchone()[0]

#     # Save metadata
#     word_count = len(generated_content.split())
#     reading_time = max(1, word_count // 200)
#     cur.execute(
#         """INSERT INTO document_metadata
#            (document_id, document_type, department, industry,
#             word_count, reading_time, template_id, status)
#            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Draft')
#            RETURNING id""",
#         (str(doc_id), document_type, department, industry,
#          word_count, reading_time, template_id),
#     )
#     meta_id = cur.fetchone()[0]

#     # Link metadata to document
#     cur.execute(
#         "UPDATE generated_documents SET metadata_id = %s WHERE id = %s",
#         (meta_id, doc_id),
#     )

#     # Save version 1.0
#     cur.execute(
#         """INSERT INTO document_versions
#            (document_id, version, content, changed_by)
#            VALUES (%s, '1.0', %s, 'AI Document Generator')""",
#         (doc_id, generated_content),
#     )

#     # Update job as completed
#     cur.execute(
#         """UPDATE generation_jobs
#            SET status = 'completed', result_doc_id = %s, completed_at = CURRENT_TIMESTAMP
#            WHERE job_id = %s""",
#         (doc_id, job_id),
#     )

#     conn.commit(); cur.close(); conn.close()
#     return str(doc_id)


# def list_documents(department: str = None, document_type: str = None, industry: str = None):
#     conn = get_connection()
#     cur = conn.cursor()

#     query = """
#         SELECT id, job_id, document_type, department, industry, status, created_at
#         FROM generated_documents WHERE 1=1
#     """
#     params = []
#     if department:
#         query += " AND department = %s"; params.append(department)
#     if document_type:
#         query += " AND document_type = %s"; params.append(document_type)
#     if industry:
#         query += " AND industry = %s"; params.append(industry)
#     query += " ORDER BY created_at DESC"

#     cur.execute(query, tuple(params))
#     rows = cur.fetchall()
#     cur.close(); conn.close()

#     return [
#         {
#             "id": str(r[0]),
#             "job_id": r[1],
#             "document_type": r[2],
#             "department": r[3],
#             "industry": r[4],
#             "status": r[5],
#             "created_at": str(r[6]),
#         }
#         for r in rows
#     ]


# def get_document(document_id: str):
#     conn = get_connection()
#     cur = conn.cursor()
#     cur.execute(
#         """SELECT gd.id, gd.job_id, gd.document_type, gd.department, gd.industry,
#                   gd.question_answers, gd.generated_content, gd.status, gd.created_at,
#                   dm.word_count, dm.reading_time, dm.status as doc_status,
#                   dm.tags, dm.compliance_tags, dm.priority, dm.confidentiality
#            FROM generated_documents gd
#            LEFT JOIN document_metadata dm ON dm.document_id = gd.id::text
#            WHERE gd.id = %s""",
#         (document_id,),
#     )
#     r = cur.fetchone()
#     cur.close(); conn.close()

#     if not r:
#         raise HTTPException(status_code=404, detail="Document not found")

#     return {
#         "id": str(r[0]),
#         "job_id": r[1],
#         "document_type": r[2],
#         "department": r[3],
#         "industry": r[4],
#         "question_answers": r[5],
#         "generated_content": r[6],
#         "status": r[7],
#         "created_at": str(r[8]),
#         "metadata": {
#             "word_count": r[9],
#             "reading_time_minutes": r[10],
#             "doc_status": r[11],
#             "tags": r[12],
#             "compliance_tags": r[13],
#             "priority": r[14],
#             "confidentiality": r[15],
#         },
#     }


# def delete_document(document_id: str):
#     conn = get_connection()
#     cur = conn.cursor()
#     cur.execute("DELETE FROM document_metadata WHERE document_id = %s", (document_id,))
#     cur.execute("DELETE FROM document_versions WHERE document_id = %s", (document_id,))
#     cur.execute(
#         "DELETE FROM generated_documents WHERE id = %s RETURNING id", (document_id,)
#     )
#     deleted = cur.fetchone()
#     conn.commit(); cur.close(); conn.close()

#     if not deleted:
#         raise HTTPException(status_code=404, detail="Document not found")

#     return {"status": "deleted", "document_id": document_id}


# def list_jobs(status: str = None):
#     conn = get_connection()
#     cur = conn.cursor()

#     query = """
#         SELECT job_id, status, document_type, department, industry,
#                result_doc_id, error_message, started_at, completed_at
#         FROM generation_jobs WHERE 1=1
#     """
#     params = []
#     if status:
#         query += " AND status = %s"; params.append(status)
#     query += " ORDER BY started_at DESC"

#     cur.execute(query, tuple(params))
#     rows = cur.fetchall()
#     cur.close(); conn.close()

#     return [
#         {
#             "job_id": r[0],
#             "status": r[1],
#             "document_type": r[2],
#             "department": r[3],
#             "industry": r[4],
#             "result_doc_id": r[5],
#             "error_message": r[6],
#             "started_at": str(r[7]),
#             "completed_at": str(r[8]) if r[8] else None,
#         }
#         for r in rows
#     ]

#--------------------------------------------------------------------------------

# """
# services/document_repository.py — matches new generated_documents + generation_jobs tables
# """
# from db import get_connection
# import json
# from fastapi import HTTPException


# def save_generated_document(
#     job_id: str,
#     industry: str,
#     document_type: str,
#     department: str,
#     question_answers: dict,
#     generated_content: str,
#     template_id: int = None,
# ):
#     conn = get_connection()
#     cursor = conn.cursor()

#     # Save document
#     cursor.execute("""
#         INSERT INTO generated_documents
#             (job_id, document_type, department, industry, question_answers, generated_content, status, template_id)
#         VALUES (%s, %s, %s, %s, %s, %s, 'completed', %s)
#         RETURNING id
#     """, (job_id, document_type, department, industry, json.dumps(question_answers), generated_content, template_id))
#     doc_id = cursor.fetchone()[0]

#     # Save metadata
#     word_count = len(generated_content.split())
#     reading_time = max(1, word_count // 200)
#     cursor.execute("""
#         INSERT INTO document_metadata
#             (document_id, document_type, department, industry, word_count, reading_time, template_id)
#         VALUES (%s, %s, %s, %s, %s, %s, %s)
#         RETURNING id
#     """, (str(doc_id), document_type, department, industry, word_count, reading_time, template_id))
#     meta_id = cursor.fetchone()[0]

#     # Link metadata back to document
#     cursor.execute("UPDATE generated_documents SET metadata_id = %s WHERE id = %s", (meta_id, doc_id))

#     # Update job status
#     cursor.execute("""
#         UPDATE generation_jobs
#         SET status = 'completed', result_doc_id = %s, completed_at = CURRENT_TIMESTAMP
#         WHERE job_id = %s
#     """, (doc_id, job_id))

#     # Save version
#     cursor.execute("""
#         INSERT INTO document_versions (document_id, version, content, changed_by)
#         VALUES (%s, '1.0', %s, 'AI Document Generator')
#     """, (doc_id, generated_content))

#     conn.commit(); cursor.close(); conn.close()
#     return str(doc_id)


# def create_job(job_id: str, document_type: str, department: str, industry: str, question_answers: dict):
#     """Create a pending job record."""
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("""
#         INSERT INTO generation_jobs (job_id, status, document_type, department, industry, question_answers)
#         VALUES (%s, 'processing', %s, %s, %s, %s)
#         ON CONFLICT (job_id) DO NOTHING
#     """, (job_id, document_type, department, industry, json.dumps(question_answers)))
#     conn.commit(); cursor.close(); conn.close()


# def fail_job(job_id: str, error: str):
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("""
#         UPDATE generation_jobs
#         SET status = 'failed', error_message = %s, completed_at = CURRENT_TIMESTAMP
#         WHERE job_id = %s
#     """, (error, job_id))
#     conn.commit(); cursor.close(); conn.close()


# def get_job_status(job_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("""
#         SELECT job_id, status, document_type, department, result_doc_id, error_message, started_at, completed_at
#         FROM generation_jobs WHERE job_id = %s
#     """, (job_id,))
#     r = cursor.fetchone()
#     cursor.close(); conn.close()
#     if not r: raise HTTPException(status_code=404, detail="Job not found")
#     return {
#         "job_id": r[0], "status": r[1], "document_type": r[2],
#         "department": r[3], "result_doc_id": r[4],
#         "error_message": r[5], "started_at": str(r[6]),
#         "completed_at": str(r[7]) if r[7] else None,
#     }


# def list_documents(department=None, document_type=None, industry=None):
#     conn = get_connection()
#     cursor = conn.cursor()
#     query = "SELECT id, job_id, document_type, department, industry, status, created_at FROM generated_documents WHERE 1=1"
#     params = []
#     if department:  query += " AND department = %s"; params.append(department)
#     if document_type: query += " AND document_type = %s"; params.append(document_type)
#     if industry:    query += " AND industry = %s"; params.append(industry)
#     query += " ORDER BY created_at DESC"
#     cursor.execute(query, tuple(params))
#     results = cursor.fetchall()
#     cursor.close(); conn.close()
#     return [{"id": str(r[0]), "job_id": r[1], "document_type": r[2], "department": r[3], "industry": r[4], "status": r[5], "created_at": str(r[6])} for r in results]


# def get_document(document_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("""
#         SELECT gd.id, gd.job_id, gd.document_type, gd.department, gd.industry,
#                gd.question_answers, gd.generated_content, gd.status, gd.created_at,
#                dm.word_count, dm.reading_time, dm.status as doc_status, dm.tags
#         FROM generated_documents gd
#         LEFT JOIN document_metadata dm ON dm.document_id = gd.id::text
#         WHERE gd.id = %s
#     """, (document_id,))
#     r = cursor.fetchone()
#     cursor.close(); conn.close()
#     if not r: raise HTTPException(status_code=404, detail="Document not found")
#     return {
#         "document_id": str(r[0]), "job_id": r[1], "document_type": r[2],
#         "department": r[3], "industry": r[4], "question_answers": r[5],
#         "generated_content": r[6], "status": r[7], "created_at": str(r[8]),
#         "word_count": r[9], "reading_time": r[10],
#         "doc_status": r[11], "tags": r[12],
#     }


# def delete_document(document_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("DELETE FROM document_metadata WHERE document_id = %s", (document_id,))
#     cursor.execute("DELETE FROM document_versions WHERE document_id = %s", (document_id,))
#     cursor.execute("DELETE FROM generated_documents WHERE id = %s RETURNING id", (document_id,))
#     deleted = cursor.fetchone()
#     conn.commit(); cursor.close(); conn.close()
#     if not deleted: raise HTTPException(status_code=404, detail="Document not found")
#     return {"status": "deleted", "document_id": document_id}

#--------------------------------------------------------------------------------
# from db import get_connection
# import json
# from fastapi import HTTPException


# def save_generated_document(
#     industry: str,
#     document_type: str,
#     department: str,
#     question_answers: dict,
#     generated_content: str,
# ):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         """
#         INSERT INTO generated_documents
#             (document_type, department, industry, question_answers, generated_content)
#         VALUES (%s, %s, %s, %s, %s)
#         RETURNING id
#         """,
#         (
#             document_type,
#             department,
#             industry,
#             json.dumps(question_answers),
#             generated_content,
#         ),
#     )

#     document_id = cursor.fetchone()[0]
#     conn.commit()
#     cursor.close()
#     conn.close()

#     return str(document_id)


# def list_documents(department: str = None, document_type: str = None, industry: str = None):
#     conn = get_connection()
#     cursor = conn.cursor()

#     query = """
#         SELECT id, document_type, department, industry, created_at
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
#     if industry:
#         query += " AND industry = %s"
#         params.append(industry)

#     query += " ORDER BY created_at DESC"

#     cursor.execute(query, tuple(params))
#     results = cursor.fetchall()

#     cursor.close()
#     conn.close()

#     return [
#         {
#             "id": str(row[0]),
#             "document_type": row[1],
#             "department": row[2],
#             "industry": row[3],
#             "created_at": str(row[4]),
#         }
#         for row in results
#     ]


# def get_document(document_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         """
#         SELECT id, document_type, department, industry, question_answers, generated_content, created_at
#         FROM generated_documents WHERE id = %s
#         """,
#         (document_id,),
#     )
#     result = cursor.fetchone()

#     cursor.close()
#     conn.close()

#     if not result:
#         raise HTTPException(status_code=404, detail="Document not found")

#     return {
#         "document_id": str(result[0]),
#         "document_type": result[1],
#         "department": result[2],
#         "industry": result[3],
#         "question_answers": result[4],
#         "generated_content": result[5],
#         "created_at": str(result[6]),
#     }


# def delete_document(document_id: str):
#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute(
#         "DELETE FROM generated_documents WHERE id = %s RETURNING id",
#         (document_id,),
#     )
#     deleted = cursor.fetchone()

#     conn.commit()
#     cursor.close()
#     conn.close()

#     if not deleted:
#         raise HTTPException(status_code=404, detail="Document not found")

#     return {"status": "deleted", "document_id": document_id}

#--------------------------------------------------------------------------------

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
