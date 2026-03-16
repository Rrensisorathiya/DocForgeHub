from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.documents      import router as documents_router
from api.templates      import router as templates_router
from api.questionnaires import router as questionnaires_router
from api.system         import router as system_router
from api.export         import router as export_router   # ← NEW

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
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# from api.documents import router as document_router
# from api.templates import router as template_router
# from api.questionnaires import router as questionnaire_router
# from api.system import router as system_router

# app = FastAPI(
#     title="SaaS Document Generation Engine",
#     description="""
# ## AI-Powered Enterprise Document Automation

# ### Workflow:
# 1. Templates & Questionnaires are **auto-seeded** from JSON files — no manual POST needed
# 2. **POST /documents/generate** — Generate document using AI
# 3. **GET /documents/** — List, retrieve, manage generated documents

# ### Tables Connected:
# `departments` · `document_types` · `templates` · `questionnaires`
# `generated_documents` · `generation_jobs` · `document_metadata`
# `document_versions` · `question_answer_logs`
# """,
#     version="2.0.0",
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# app.include_router(document_router,      prefix="/documents",      tags=["Documents"])
# app.include_router(template_router,      prefix="/templates",      tags=["Templates"])
# app.include_router(questionnaire_router, prefix="/questionnaires", tags=["Questionnaires"])
# app.include_router(system_router,        prefix="/system",         tags=["System"])


# @app.get("/", tags=["Root"])
# def root():
#     return {
#         "app": "SaaS Document Generation Engine",
#         "version": "2.0.0",
#         "docs": "/docs",
#         "endpoints": {
#             "Documents": {
#                 "POST /documents/generate":      "Generate AI document",
#                 "GET  /documents/":              "List all documents",
#                 "GET  /documents/{id}":          "Get document by ID",
#                 "DELETE /documents/{id}":        "Delete document",
#                 "GET  /documents/job/{job_id}":  "Check job status",
#                 "GET  /documents/jobs":          "List all jobs",
#             },
#             "Templates": {
#                 "GET /templates/":               "List all templates (seeded from content.json)",
#                 "GET /templates/{id}":           "Get template by ID",
#             },
#             "Questionnaires": {
#                 "GET /questionnaires/":          "List all questionnaires",
#                 "GET /questionnaires/{id}":      "Get questionnaire by ID",
#             },
#             "System": {
#                 "GET /system/health":            "Health check + DB status",
#                 "GET /system/stats":             "Database statistics",
#                 "GET /system/version":           "API version",
#             },
#         },
#     }

#---------------------------------------------------------------------

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# from api.documents import router as document_router
# from api.templates import router as template_router
# from api.questionnaires import router as questionnaire_router
# from api.system import router as system_router

# app = FastAPI(
#     title="SaaS Document Generation Engine",
#     description="""
# ## AI-Powered Enterprise Document Automation

# ### How to use:

# **Step 1** — Templates & Questionnaires are auto-loaded from JSON files.
# No manual creation needed.

# **Step 2** — Generate a Document (`POST /documents/generate`)
# Pass `industry`, `department`, `document_type`, and `question_answers`.

# **Step 3** — Manage Documents (`GET`, `DELETE /documents/`)
# List, retrieve, or delete generated documents.
# """,
#     version="2.0.0",
# )

# # CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Routers
# app.include_router(document_router,      prefix="/documents",      tags=["Documents"])
# app.include_router(template_router,      prefix="/templates",      tags=["Templates"])
# app.include_router(questionnaire_router, prefix="/questionnaires", tags=["Questionnaires"])
# app.include_router(system_router,        prefix="/system",         tags=["System"])


# @app.get("/", tags=["Root"])
# def root():
#     return {
#         "message": "SaaS Document Generation Engine",
#         "version": "2.0.0",
#         "docs": "/docs",
#         "endpoints": {
#             "generate_document":   "POST /documents/generate",
#             "list_documents":      "GET  /documents/",
#             "get_document":        "GET  /documents/{id}",
#             "delete_document":     "DELETE /documents/{id}",
#             "check_job":           "GET  /documents/job/{job_id}",
#             "list_templates":      "GET  /templates/",
#             "get_template":        "GET  /templates/{id}",
#             "list_questionnaires": "GET  /questionnaires/",
#             "get_questionnaire":   "GET  /questionnaires/{id}",
#             "health":              "GET  /system/health",
#             "version":             "GET  /system/version",
#         }
#     }

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from api.documents import router as document_router
# from api.templates import router as template_router
# from api.questionnaires import router as questionnaire_router
# from api.system import router as system_router

# app = FastAPI(
#     title="SaaS Document Generation Engine",
#     description="""
# ## AI-Powered Enterprise Document Automation

# ### How to use this API:

# **Step 1** — Create a Template (`POST /templates/`)
# Define the document type and its sections.

# **Step 2** — Create a Questionnaire (`POST /questionnaires/`) *(optional but recommended)*
# Define what questions users should answer.

# **Step 3** — Generate a Document (`POST /documents/generate`)
# Pass `industry`, `department`, `document_type`, and your `question_answers`.
# The AI will generate each section and return the full document.

# **Step 4** — Manage Documents (`GET`, `DELETE /documents/`)
# List, retrieve, or delete generated documents.
# """,
#     version="2.0.0",
# )

# # CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Routers
# app.include_router(document_router, prefix="/documents", tags=["Documents"])
# app.include_router(template_router, prefix="/templates", tags=["Templates"])
# app.include_router(questionnaire_router, prefix="/questionnaires", tags=["Questionnaires"])
# app.include_router(system_router, prefix="/system", tags=["System"])


# @app.get("/", tags=["Root"])
# def root():
#     return {
#         "message": "SaaS Document Generation Engine is running",
#         "version": "2.0.0",
#         "docs": "/docs",
#         "quickstart": {
#             "step_1": "POST /templates/ — create a template",
#             "step_2": "POST /questionnaires/ — create a questionnaire (optional)",
#             "step_3": "POST /documents/generate — generate your document",
#             "step_4": "GET /documents/ — list all documents",
#         },
#     }

#--------------------------------------------------------------------------------

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# # Routers
# from api.documents import router as document_router
# from api.templates import router as template_router
# from api.questionnaires import router as questionnaire_router
# from api.metadata import router as metadata_router
# from api.system import router as system_router

# app = FastAPI(
#     title="SaaS Document Generation Engine",
#     description="Enterprise AI-powered SaaS Document Automation Platform",
#     version="1.0.0",
# )

# # CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Include Routers
# app.include_router(document_router, prefix="/documents", tags=["Documents"])
# app.include_router(template_router, prefix="/templates", tags=["Templates"])
# app.include_router(questionnaire_router, prefix="/questionnaires", tags=["Questionnaires"])
# app.include_router(metadata_router, prefix="/metadata", tags=["Metadata"])
# app.include_router(system_router, prefix="/system", tags=["System"])

# @app.get("/", tags=["Root"])
# def root():
#     return {
#         "message": "SaaS Document Generation Engine Running",
#         "version": "1.0.0",
#         "docs": "/docs"
#     }

# # from fastapi import FastAPI
# # from api.documents import router as document_router

# # app = FastAPI(
# #     title="SaaS Document Generation Engine",
# #     version="1.0.0"
# # )

# # app.include_router(document_router, prefix="/documents", tags=["Documents"])


# # @app.get("/")
# # def health_check():
# #     return {"status": "API running successfully"}
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from api.documents import router as document_router

# app = FastAPI(
#     title="SaaS Document Generation Engine",
#     description="Enterprise AI-powered SaaS Document Automation Platform",
#     version="1.0.0",
# )

# # -------------------------------------------
# # CORS (Important for frontend later)
# # -------------------------------------------
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Change in production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # -------------------------------------------
# # Include Routers
# # -------------------------------------------
# app.include_router(
#     document_router,
#     prefix="/documents",
#     tags=["Documents"],
# )

# # -------------------------------------------
# # Root Endpoint
# # -------------------------------------------
# @app.get("/", tags=["Root"])
# def root():
#     return {
#         "message": "SaaS Document Generation Engine is running",
#         "version": "1.0.0",
#         "docs": "/docs"
#     }

# # -------------------------------------------
# # Health Check
# # -------------------------------------------
# @app.get("/health", tags=["System"])
# def health_check():
#     return {"status": "healthy"}
