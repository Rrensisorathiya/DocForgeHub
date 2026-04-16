from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.documents      import router as documents_router
from api.templates      import router as templates_router
from api.questionnaires import router as questionnaires_router
from api.system         import router as system_router
from api.export         import router as export_router   # ← NEW
from api.retrieve import router as rag_router
from api.assistant_router import router as assistant_router, ticket_router

from utils.logger import setup_logger

logger = setup_logger(__name__)

logger.info("Application started")

app = FastAPI(
    title="DocForgeHub API",
    description="AI-Powered Enterprise Document Generation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────
app.include_router(documents_router,      prefix="/documents",      tags=["Documents"])
app.include_router(templates_router,      prefix="/templates",      tags=["Templates"])
app.include_router(questionnaires_router, prefix="/questionnaires", tags=["Questionnaires"])
app.include_router(system_router,         prefix="/system",         tags=["System"])
app.include_router(export_router,         prefix="/export",         tags=["Export"])  # ← NEW


@app.get("/")
def root():
    return {
        "message": "DocForgeHub API is running",
        "docs": "/docs",
        "endpoints": {
            "documents":      "/documents/",
            "templates":      "/templates/",
            "questionnaires": "/questionnaires/",
            "system":         "/system/health",
            "export_docx":    "/export/{document_id}/docx",
            "export_pdf":     "/export/{document_id}/pdf",
        }
    }

app.include_router(rag_router)
app.include_router(assistant_router)
app.include_router(ticket_router)

