from fastapi import APIRouter
from db import get_connection
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


@router.get("/health", summary="Health check")
def health_check():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close(); conn.close()
        db_status = "connected"
        logger.debug("Health check: Database connection successful")
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error(f"Health check: Database connection failed - {str(e)}")

    return {
        "status": "healthy",
        "database": db_status,
        "version": "2.0.0",
    }


@router.get("/version", summary="API version")
def version():
    logger.debug("Version endpoint called")
    return {
        "version": "2.0.0",
        "engine": "SaaS Document Generation Engine",
    }


@router.get("/stats", summary="Database statistics")
def stats():
    logger.info("Generating database statistics")
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM templates")
        templates = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM questionnaires")
        questionnaires = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM generated_documents")
        documents = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM generation_jobs")
        jobs = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM generation_jobs WHERE status = 'completed'")
        completed = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM generation_jobs WHERE status = 'failed'")
        failed = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM departments")
        departments = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM document_types")
        doc_types = cur.fetchone()[0]

        cur.close(); conn.close()
        
        logger.debug(f"Stats: {documents} documents, {jobs} jobs ({completed} completed, {failed} failed)")

        return {
            "templates":       templates,
            "questionnaires":  questionnaires,
            "documents_generated": documents,
            "total_jobs":      jobs,
            "jobs_completed":  completed,
            "jobs_failed":     failed,
            "departments":     departments,
            "document_types":  doc_types,
        }
    except Exception as e:
        logger.error(f"Failed to generate statistics: {str(e)}", exc_info=True)
        raise
