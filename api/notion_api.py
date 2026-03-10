import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from services.notion_service import (
    test_notion_connection,
    publish_document_to_notion,
    list_notion_pages,
)
from services.document_repository import get_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notion", tags=["Notion"])


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class NotionCredentials(BaseModel):
    token:       str = Field(..., description="Notion integration secret (secret_xxxx)")
    database_id: str = Field(..., description="Notion database UUID")


class PublishRequest(BaseModel):
    token:       str = Field(..., description="Notion integration secret")
    database_id: str = Field(..., description="Target Notion database UUID")

    # Provide document_id OR content — document_id is preferred
    document_id: Optional[str] = Field(None, description="DB document ID — content fetched automatically")
    content:     Optional[str] = Field(None, description="Raw text (only if document_id not given)")
    title:       Optional[str] = Field(None, description="Page title (auto-built from DB if document_id given)")

    # Metadata
    doc_type:           Optional[str]       = Field(None)
    industry:           Optional[str]       = Field(None)
    version:            Optional[str]       = Field(None)
    tags:               Optional[list[str]] = Field(None)
    created_by:         Optional[str]       = Field(None)
    status:             Optional[str]       = Field(None)
    source_template_id: Optional[str]       = Field(None)
    source_prompts:     Optional[str]       = Field(None)


class ListPagesRequest(BaseModel):
    token:       str = Field(..., description="Notion integration secret")
    database_id: str = Field(..., description="Notion database UUID")
    limit:       int = Field(20, ge=1, le=100)


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@router.post("/test-connection", summary="Test Notion credentials")
async def test_connection(body: NotionCredentials):
    result = test_notion_connection(token=body.token, database_id=body.database_id)
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return result


@router.post("/publish", summary="Publish document to Notion (flat, readable page)")
async def publish_document(body: PublishRequest):
    """
    Publish a document to Notion as a flat, readable page.

    Content is written directly onto the page as headings + blocks + dividers.
    No collapsible toggles — everything is immediately visible.

    Long documents are automatically split into sections and appended in
    batches to respect Notion's 100-block-per-request limit.

    Pass document_id (recommended):
        { "token": "...", "database_id": "...", "document_id": "42" }

    Or pass raw content:
        { "token": "...", "database_id": "...", "title": "My Doc", "content": "..." }
    """

    # ── Resolve content from DB if document_id given ──────────────────
    resolved_title    = body.title
    resolved_content  = body.content
    resolved_type     = body.doc_type
    resolved_industry = body.industry

    if body.document_id:
        try:
            doc = get_document(body.document_id)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{body.document_id}' not found.",
            )

        resolved_content  = doc.get("generated_content", "")
        resolved_type     = body.doc_type     or doc.get("document_type", "")
        resolved_industry = body.industry     or doc.get("industry", "")

        if not resolved_title:
            doc_type   = doc.get("document_type", "Document")
            department = doc.get("department", "")
            resolved_title = f"{doc_type} — {department}".strip(" —")

        logger.info(
            f"document_id={body.document_id} resolved → "
            f"'{resolved_title}' ({len(resolved_content or '')} chars)"
        )

    # ── Validate ──────────────────────────────────────────────────────
    if not resolved_title or not resolved_title.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot determine document title. Pass 'title' explicitly.",
        )

    if not resolved_content or not resolved_content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Document content is empty. "
                "If using document_id, confirm generated_content is saved in the DB. "
                "If passing content directly, ensure it is not empty."
            ),
        )

    logger.info(
        f"Publishing '{resolved_title}' | {len(resolved_content)} chars | "
        f"type={resolved_type} | industry={resolved_industry}"
    )

    # ── Publish ───────────────────────────────────────────────────────
    result = publish_document_to_notion(
        token=body.token,
        database_id=body.database_id,
        title=resolved_title,
        content=resolved_content,
        doc_type=resolved_type,
        industry=resolved_industry,
        version=body.version,
        tags=body.tags,
        created_by=body.created_by,
        status=body.status,
        source_template_id=body.source_template_id,
        source_prompts=body.source_prompts,
    )

    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    logger.info(
        f"Published '{resolved_title}' → {result['page_id']} "
        f"({result.get('sections_written', '?')} sections)"
    )
    return result


@router.post("/pages", summary="List recently published pages")
async def get_pages(body: ListPagesRequest):
    result = list_notion_pages(
        token=body.token,
        database_id=body.database_id,
        limit=body.limit,
    )
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return result
# """
# Notion API Routes
# ─────────────────
# POST /api/notion/test-connection   → Test token + database access
# POST /api/notion/publish           → Publish a document to Notion
# GET  /api/notion/pages             → List recently published pages
# """

# import logging
# from typing import Optional
# from fastapi import APIRouter, HTTPException, status
# from pydantic import BaseModel, Field

# from services.notion_service import (
#     test_notion_connection,
#     publish_document_to_notion,
#     list_notion_pages,
# )

# logger = logging.getLogger(__name__)

# router = APIRouter(prefix="/api/notion", tags=["Notion"])


# # ─────────────────────────────────────────────
# # Request / Response Models
# # ─────────────────────────────────────────────

# class NotionCredentials(BaseModel):
#     token:       str = Field(..., description="Notion integration secret (secret_xxxx)")
#     database_id: str = Field(..., description="Notion database UUID")


# class PublishRequest(BaseModel):
#     token:       str = Field(..., description="Notion integration secret")
#     database_id: str = Field(..., description="Target Notion database UUID")
#     title:       str = Field(..., description="Document title")
#     content:     str = Field(..., description="Full document text content")
#     status:      Optional[str]       = Field(None, description="Value for a 'Status' select column")
#     tags:        Optional[list[str]] = Field(None, description="Tags for a multi-select column")


# class ListPagesRequest(BaseModel):
#     token:       str = Field(..., description="Notion integration secret")
#     database_id: str = Field(..., description="Notion database UUID")
#     limit:       int = Field(20, ge=1, le=100)


# # ─────────────────────────────────────────────
# # Endpoints
# # ─────────────────────────────────────────────

# @router.post(
#     "/test-connection",
#     summary="Test Notion credentials",
#     response_description="Connection status and database info",
# )
# async def test_connection(body: NotionCredentials):
#     """
#     Verify the integration token and confirm the database is accessible.
#     Returns the database name and its column/property names.
#     """
#     result = test_notion_connection(
#         token=body.token,
#         database_id=body.database_id,
#     )

#     if not result["success"]:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=result["error"],
#         )

#     return result


# @router.post(
#     "/publish",
#     summary="Publish document to Notion",
#     response_description="Created page ID and URL",
# )
# async def publish_document(body: PublishRequest):
#     """
#     Create a new page in the target Notion database using the document content.
#     The page title maps to the database's title column.
#     Optional status and tags map to 'Status' (select) and 'Tags' (multi-select) columns.
#     """
#     if not body.title.strip():
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail="Document title cannot be empty.",
#         )

#     if not body.content.strip():
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail="Document content cannot be empty.",
#         )

#     result = publish_document_to_notion(
#         token=body.token,
#         database_id=body.database_id,
#         title=body.title,
#         content=body.content,
#         status=body.status,
#         tags=body.tags,
#     )

#     if not result["success"]:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=result["error"],
#         )

#     logger.info(f"Document '{body.title}' published to Notion page {result['page_id']}")
#     return result


# @router.post(
#     "/pages",
#     summary="List recently published pages",
#     response_description="List of pages in the database",
# )
# async def get_pages(body: ListPagesRequest):
#     """
#     Retrieve the most recently created pages from the Notion database.
#     Useful to confirm successful publishing or show a history list in the UI.
#     """
#     result = list_notion_pages(
#         token=body.token,
#         database_id=body.database_id,
#         limit=body.limit,
#     )

#     if not result["success"]:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=result["error"],
#         )

#     return result