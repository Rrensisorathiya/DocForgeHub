from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.documents import router as document_router
from api.templates import router as template_router
from api.questionnaires import router as questionnaire_router
from api.system import router as system_router

app = FastAPI(
    title="SaaS Document Generation Engine",
    description="""
## AI-Powered Enterprise Document Automation

### How to use this API:

**Step 1** — Create a Template (`POST /templates/`)
Define the document type and its sections.

**Step 2** — Create a Questionnaire (`POST /questionnaires/`) *(optional but recommended)*
Define what questions users should answer.

**Step 3** — Generate a Document (`POST /documents/generate`)
Pass `industry`, `department`, `document_type`, and your `question_answers`.
The AI will generate each section and return the full document.

**Step 4** — Manage Documents (`GET`, `DELETE /documents/`)
List, retrieve, or delete generated documents.
""",
    version="2.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(document_router, prefix="/documents", tags=["Documents"])
app.include_router(template_router, prefix="/templates", tags=["Templates"])
app.include_router(questionnaire_router, prefix="/questionnaires", tags=["Questionnaires"])
app.include_router(system_router, prefix="/system", tags=["System"])


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "SaaS Document Generation Engine is running",
        "version": "2.0.0",
        "docs": "/docs",
        "quickstart": {
            "step_1": "POST /templates/ — create a template",
            "step_2": "POST /questionnaires/ — create a questionnaire (optional)",
            "step_3": "POST /documents/generate — generate your document",
            "step_4": "GET /documents/ — list all documents",
        },
    }

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
