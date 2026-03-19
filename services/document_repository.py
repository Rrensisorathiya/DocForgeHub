from db import get_connection
from fastapi import HTTPException
import json
from utils.logger import setup_logger

logger = setup_logger(__name__)


def create_job(job_id: str, document_type: str, department: str, industry: str, question_answers: dict):
    try:
        logger.debug(f"Creating job: {job_id} - Type: {document_type}, Department: {department}")
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
        logger.info(f"Job created successfully: {job_id}")
    except Exception as e:
        logger.error(f"Failed to create job {job_id}: {str(e)}", exc_info=True)
        raise


def fail_job(job_id: str, error: str):
    try:
        logger.warning(f"Failing job {job_id} with error: {error}")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """UPDATE generation_jobs
               SET status = 'failed', error_message = %s, completed_at = CURRENT_TIMESTAMP
               WHERE job_id = %s""",
            (error, job_id),
        )
        conn.commit(); cur.close(); conn.close()
        logger.info(f"Job {job_id} marked as failed")
    except Exception as e:
        logger.error(f"Failed to update job status for {job_id}: {str(e)}", exc_info=True)
        raise


def get_job_status(job_id: str):
    try:
        logger.debug(f"Fetching job status for: {job_id}")
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
            logger.warning(f"Job not found: {job_id}")
            raise HTTPException(status_code=404, detail="Job not found")

        logger.debug(f"Job status retrieved: {job_id} - Status: {r[1]}")
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {str(e)}", exc_info=True)
        raise


def save_generated_document(
    job_id: str,
    industry: str,
    document_type: str,
    department: str,
    question_answers: dict,
    generated_content: str,
    template_id: int = None,
):
    logger.info(f"Saving generated document - Job: {job_id}, Type: {document_type}, Department: {department}")
    
    # Run validation before saving
    try:
        from services.document_validator import validate_document
        logger.debug(f"Running validation for document before save")
        validation = validate_document(
            content=generated_content,
            doc_type=document_type,
            department=department,
            question_answers=question_answers,
        )
        logger.debug(f"Validation complete - Score: {validation.get('score')}, Grade: {validation.get('grade')}")
    except Exception as e:
        logger.warning(f"Validation failed, using default: {str(e)}")
        validation = {"score": 0, "grade": "N/A", "valid": True, "word_count": len(generated_content.split())}

    try:
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
        logger.debug(f"Document inserted with ID: {doc_id}")

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
        logger.debug(f"Document metadata inserted with ID: {meta_id}")

        cur.execute(
            "UPDATE generated_documents SET metadata_id = %s WHERE id = %s",
            (meta_id, doc_id),
        )

        changed_by = f"AI Generator | Score: {validation.get('score',0)}/100 | Grade: {validation.get('grade','N/A')}"
        # Versioning logic: get latest version and increment
        cur.execute(
            "SELECT version FROM document_versions WHERE document_id = %s ORDER BY version DESC LIMIT 1",
            (doc_id,)
        )
        last_version_row = cur.fetchone()
        if last_version_row:
            try:
                last_version = float(last_version_row[0])
                new_version = f"{last_version + 1:.1f}"
            except Exception:
                new_version = "2.0"
        else:
            new_version = "1.0"
        cur.execute(
            """INSERT INTO document_versions
               (document_id, version, content, changed_by)
               VALUES (%s, %s, %s, %s)""",
            (doc_id, new_version, generated_content, changed_by),
        )
        logger.debug(f"Document version {new_version} created")

        cur.execute(
            """UPDATE generation_jobs
               SET status = 'completed', result_doc_id = %s, completed_at = CURRENT_TIMESTAMP
               WHERE job_id = %s""",
            (doc_id, job_id),
        )

        conn.commit(); cur.close(); conn.close()
        logger.info(f"Document saved successfully - Doc ID: {doc_id}, Job: {job_id}")
        
        # ── Auto-sync to Notion (non-blocking) ──
        try:
            # --- HARDCODED NOTION CREDENTIALS ---
            notion_token = "ntn_Y5797487239LBvOExbL66xiAMcyIF9owRFZCVOIJEVZ2XT"  # <-- REPLACE with your Notion integration token
            notion_db_id = "899d4d8f-8a85-4c9f-b0b2-0d2bb8055153"        # <-- REPLACE with your Notion database ID

            logger.debug(f"Syncing document {doc_id} to Notion")
            from services.notion_service import publish_to_notion

            # Ensure schema columns exist
            conn_schema = get_connection()
            cur_schema = conn_schema.cursor()
            cur_schema.execute("ALTER TABLE generated_documents ADD COLUMN IF NOT EXISTS notion_page_id TEXT")
            cur_schema.execute("ALTER TABLE generated_documents ADD COLUMN IF NOT EXISTS notion_url TEXT")
            cur_schema.execute("ALTER TABLE generated_documents ADD COLUMN IF NOT EXISTS notion_published BOOLEAN DEFAULT FALSE")
            conn_schema.commit(); cur_schema.close(); conn_schema.close()

            company_name = question_answers.get("company_name", "Not Specified")
            notion_result = publish_to_notion(
                token=notion_token,
                db_id=notion_db_id,
                document_type=document_type,
                department=department,
                industry=industry,
                content=generated_content,
                company=company_name,
                version=new_version,
                score=validation.get("score"),
                grade=validation.get("grade"),
                word_count=word_count,
            )
            logger.info(f"Document synced to Notion - Page ID: {notion_result.get('page_id')}")

            # Store Notion page ID in database
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                """UPDATE generated_documents 
                       SET notion_page_id = %s, notion_url = %s, notion_published = TRUE
                       WHERE id = %s""",
                (notion_result.get('page_id'), notion_result.get('url'), doc_id)
            )
            conn.commit(); cur.close(); conn.close()
        except Exception as e:
            logger.warning(f"Failed to sync document {doc_id} to Notion (non-blocking): {str(e)}")
            # Don't raise - document is already saved successfully in DB
        
        return str(doc_id), validation
    except Exception as e:
        logger.error(f"Failed to save generated document for job {job_id}: {str(e)}", exc_info=True)
        raise


def list_documents(department: str = None, document_type: str = None, industry: str = None):
    logger.debug(f"Listing documents - Filters: department={department}, type={document_type}, industry={industry}")
    try:
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
        
        logger.debug(f"Retrieved {len(rows)} documents")

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
    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}", exc_info=True)
        raise


def get_document(document_id: str):
    logger.debug(f"Retrieving document: {document_id}")
    try:
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
            logger.warning(f"Document not found: {document_id}")
            raise HTTPException(status_code=404, detail="Document not found")

        logger.debug(f"Document retrieved: {document_id} - Type: {r[2]}")
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve document {document_id}: {str(e)}", exc_info=True)
        raise


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

def delete_document(document_id: str):
    """Delete a document and all related records in correct FK order."""
    logger.info(f"Deleting document: {document_id}")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Check document exists
            logger.debug(f"Checking if document {document_id} exists")
            cur.execute("SELECT id, metadata_id FROM generated_documents WHERE id = %s", (document_id,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"Document not found for deletion: {document_id}")
                raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
            
            metadata_id = row[1]  # get metadata_id before deleting

            # 2. Nullify generation_jobs.result_doc_id FK
            logger.debug(f"Nullifying generation_jobs references for document {document_id}")
            cur.execute(
                "UPDATE generation_jobs SET result_doc_id = NULL WHERE result_doc_id = %s",
                (int(document_id),)
            )

            # 3. Nullify generated_documents.metadata_id FK (circular reference fix)
            logger.debug(f"Nullifying metadata_id for document {document_id}")
            cur.execute(
                "UPDATE generated_documents SET metadata_id = NULL WHERE id = %s",
                (int(document_id),)
            )

            # 4. Delete document_versions FK -> generated_documents.id
            logger.debug(f"Deleting document versions for document {document_id}")
            cur.execute(
                "DELETE FROM document_versions WHERE document_id = %s",
                (int(document_id),)
            )

            # 5. Delete document_metadata
            if metadata_id:
                logger.debug(f"Deleting document metadata {metadata_id}")
                cur.execute(
                    "DELETE FROM document_metadata WHERE id = %s",
                    (metadata_id,)
                )
            else:
                logger.debug(f"Deleting document metadata by document_id {document_id}")
                cur.execute(
                    "DELETE FROM document_metadata WHERE document_id = %s",
                    (str(document_id),)
                )

            # 6. Now safe to delete the document
            logger.debug(f"Deleting generated_documents record for {document_id}")
            cur.execute(
                "DELETE FROM generated_documents WHERE id = %s",
                (int(document_id),)
            )

        conn.commit()
        logger.info(f"Document deleted successfully: {document_id}")
        return {"status": "deleted", "document_id": document_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {str(e)}", exc_info=True)
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
    finally:
        conn.close()

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


def list_jobs(status: str = None):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT job_id, status, document_type, department, industry,
               result_doc_id, error_message, started_at, completed_at
        FROM generation_jobs
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND status = %s"
        params.append(status)
    query += " ORDER BY started_at DESC LIMIT 50"

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "job_id":        r[0],
            "status":        r[1],
            "document_type": r[2],
            "department":    r[3],
            "industry":      r[4],
            "result_doc_id": r[5],  # will be None after document deleted — that's fine
            "error_message": r[6],
            "started_at":    str(r[7]),
            "completed_at":  str(r[8]) if r[8] else None,
        }
        for r in rows
    ]

"""
ADDITION to services/document_repository.py
Add this function at the bottom of your existing document_repository.py
"""

# ─── ADD THIS FUNCTION to your existing document_repository.py ───

def mark_published(document_id: str, notion_page_id: str, notion_url: str):
    """Mark a document as published to Notion."""
    try:
        from db import get_connection
        conn = get_connection()
        cur = conn.cursor()

        # Try to add columns if they don't exist
        try:
            cur.execute("ALTER TABLE generated_documents ADD COLUMN IF NOT EXISTS notion_page_id TEXT")
            cur.execute("ALTER TABLE generated_documents ADD COLUMN IF NOT EXISTS notion_url TEXT")
            cur.execute("ALTER TABLE generated_documents ADD COLUMN IF NOT EXISTS notion_published BOOLEAN DEFAULT FALSE")
            conn.commit()
        except Exception:
            conn.rollback()

        cur.execute("""
            UPDATE generated_documents
            SET notion_page_id = %s,
                notion_url = %s,
                notion_published = TRUE
            WHERE id = %s
        """, (notion_page_id, notion_url, document_id))

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Warning: could not mark published: {e}")

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
