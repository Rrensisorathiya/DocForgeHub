"""
Notion API Routes
─────────────────
POST /api/notion/test-connection   → Test token + database access
POST /api/notion/publish           → Publish a document to Notion
GET  /api/notion/pages             → List recently published pages
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from services.notion_service import (
    test_notion_connection,
    publish_document_to_notion,
    list_notion_pages,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notion", tags=["Notion"])


# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────

class NotionCredentials(BaseModel):
    token:       str = Field(..., description="Notion integration secret (secret_xxxx)")
    database_id: str = Field(..., description="Notion database UUID")


class PublishRequest(BaseModel):
    token:       str = Field(..., description="Notion integration secret")
    database_id: str = Field(..., description="Target Notion database UUID")
    title:       str = Field(..., description="Document title")
    content:     str = Field(..., description="Full document text content")
    status:      Optional[str]       = Field(None, description="Value for a 'Status' select column")
    tags:        Optional[list[str]] = Field(None, description="Tags for a multi-select column")


class ListPagesRequest(BaseModel):
    token:       str = Field(..., description="Notion integration secret")
    database_id: str = Field(..., description="Notion database UUID")
    limit:       int = Field(20, ge=1, le=100)


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@router.post(
    "/test-connection",
    summary="Test Notion credentials",
    response_description="Connection status and database info",
)
async def test_connection(body: NotionCredentials):
    """
    Verify the integration token and confirm the database is accessible.
    Returns the database name and its column/property names.
    """
    result = test_notion_connection(
        token=body.token,
        database_id=body.database_id,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )

    return result


@router.post(
    "/publish",
    summary="Publish document to Notion",
    response_description="Created page ID and URL",
)
async def publish_document(body: PublishRequest):
    """
    Create a new page in the target Notion database using the document content.
    The page title maps to the database's title column.
    Optional status and tags map to 'Status' (select) and 'Tags' (multi-select) columns.
    """
    if not body.title.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document title cannot be empty.",
        )

    if not body.content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document content cannot be empty.",
        )

    result = publish_document_to_notion(
        token=body.token,
        database_id=body.database_id,
        title=body.title,
        content=body.content,
        status=body.status,
        tags=body.tags,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )

    logger.info(f"Document '{body.title}' published to Notion page {result['page_id']}")
    return result


@router.post(
    "/pages",
    summary="List recently published pages",
    response_description="List of pages in the database",
)
async def get_pages(body: ListPagesRequest):
    """
    Retrieve the most recently created pages from the Notion database.
    Useful to confirm successful publishing or show a history list in the UI.
    """
    result = list_notion_pages(
        token=body.token,
        database_id=body.database_id,
        limit=body.limit,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )

    return result