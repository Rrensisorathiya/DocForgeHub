"""
Notion Integration Service
Handles all communication with the Notion API:
  - Connection testing
  - Publishing documents as Notion pages
  - Fetching database schema (column names)
"""

import logging
from typing import Optional
from notion_client import Client
from notion_client.errors import APIResponseError

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Helper: build a Notion client
# ─────────────────────────────────────────────

def _get_client(token: str) -> Client:
    return Client(auth=token)


# ─────────────────────────────────────────────
# 1. Test Connection
# ─────────────────────────────────────────────

def test_notion_connection(token: str, database_id: str) -> dict:
    """
    Verify that the integration token is valid and the database is accessible.

    Returns:
        {
            "success": True,
            "database_name": "My DB",
            "properties": ["Name", "Status", "Tags", ...]
        }
        OR
        {"success": False, "error": "...reason..."}
    """
    try:
        notion = _get_client(token)
        db = notion.databases.retrieve(database_id=database_id)

        # Extract database title
        title_arr = db.get("title", [])
        db_name = title_arr[0]["plain_text"] if title_arr else "Untitled Database"

        # Extract property/column names
        properties = list(db.get("properties", {}).keys())

        logger.info(f"Notion connection successful. DB: '{db_name}', Properties: {properties}")
        return {
            "success": True,
            "database_name": db_name,
            "properties": properties,
        }

    except APIResponseError as e:
        error_map = {
            "unauthorized":       "Invalid integration token. Re-copy it from notion.so/my-integrations.",
            "object_not_found":   "Database not found. Make sure you shared the database with your integration.",
            "restricted_resource":"This integration does not have access to the database.",
        }
        msg = error_map.get(e.code, f"Notion API error ({e.code}): {e.message}")
        logger.error(f"Notion API error during test: {msg}")
        return {"success": False, "error": msg}

    except Exception as e:
        logger.exception("Unexpected error during Notion connection test")
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────
# 2. Publish Document
# ─────────────────────────────────────────────

def publish_document_to_notion(
    token: str,
    database_id: str,
    title: str,
    content: str,
    status: Optional[str] = None,
    tags: Optional[list[str]] = None,
    extra_properties: Optional[dict] = None,
) -> dict:
    """
    Create a new page in a Notion database with the given document content.

    Args:
        token:            Notion integration secret token.
        database_id:      Target Notion database ID.
        title:            Document title → goes into the Title/Name column.
        content:          Full document text → becomes paragraph blocks on the page.
        status:           Optional value for a 'Status' select column.
        tags:             Optional list of tag strings for a 'Tags' multi-select column.
        extra_properties: Any additional Notion property dicts to merge in.

    Returns:
        {"success": True, "page_id": "...", "page_url": "https://notion.so/..."}
        OR
        {"success": False, "error": "...reason..."}
    """
    try:
        notion = _get_client(token)

        # ── Fetch DB to find the real title-column name ──────────────────
        db = notion.databases.retrieve(database_id=database_id)
        title_prop_name = _find_title_property(db)

        # ── Build properties ─────────────────────────────────────────────
        properties: dict = {
            title_prop_name: {
                "title": [{"text": {"content": title[:2000]}}]
            }
        }

        db_props = db.get("properties", {})

        if status and "Status" in db_props:
            properties["Status"] = {"select": {"name": status}}

        if tags and "Tags" in db_props:
            properties["Tags"] = {"multi_select": [{"name": t} for t in tags]}

        if extra_properties:
            properties.update(extra_properties)

        # ── Build content blocks ─────────────────────────────────────────
        children = _text_to_blocks(content)

        # ── Create the page ──────────────────────────────────────────────
        response = notion.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=children[:100],   # Notion allows max 100 blocks per request
        )

        page_id  = response["id"]
        page_url = response.get("url", "")

        # If content was long, append remaining blocks
        if len(children) > 100:
            _append_blocks(notion, page_id, children[100:])

        logger.info(f"Published to Notion. Page ID: {page_id}")
        return {"success": True, "page_id": page_id, "page_url": page_url}

    except APIResponseError as e:
        error_map = {
            "unauthorized":       "Invalid integration token.",
            "object_not_found":   "Database not found or not shared with integration.",
            "validation_error":   f"Notion validation error: {e.message} — check your database column names.",
        }
        msg = error_map.get(e.code, f"Notion API error ({e.code}): {e.message}")
        logger.error(f"Notion API error during publish: {msg}")
        return {"success": False, "error": msg}

    except Exception as e:
        logger.exception("Unexpected error during Notion publish")
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────
# 3. List Pages (optional helper for frontend)
# ─────────────────────────────────────────────

def list_notion_pages(token: str, database_id: str, limit: int = 20) -> dict:
    """
    Return recently created pages from the database (for display / confirmation).
    """
    try:
        notion = _get_client(token)
        response = notion.databases.query(
            database_id=database_id,
            page_size=limit,
            sorts=[{"timestamp": "created_time", "direction": "descending"}],
        )

        pages = []
        for page in response.get("results", []):
            title = _extract_page_title(page)
            pages.append({
                "id":         page["id"],
                "title":      title,
                "url":        page.get("url", ""),
                "created_at": page.get("created_time", ""),
            })

        return {"success": True, "pages": pages}

    except APIResponseError as e:
        return {"success": False, "error": f"Notion API error ({e.code}): {e.message}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────
# Private Helpers
# ─────────────────────────────────────────────

def _find_title_property(db: dict) -> str:
    """Return the name of the title-type property in the database."""
    for name, prop in db.get("properties", {}).items():
        if prop.get("type") == "title":
            return name
    return "Name"   # sensible fallback


def _text_to_blocks(text: str) -> list[dict]:
    """
    Convert a plain-text string into Notion paragraph blocks.
    Splits on double newlines (paragraphs) and respects Notion's 2000-char block limit.
    """
    if not text:
        return []

    blocks = []
    paragraphs = text.split("\n\n") if "\n\n" in text else [text]

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # Split into ≤2000-char chunks
        for i in range(0, len(para), 2000):
            chunk = para[i : i + 2000]
            blocks.append({
                "object": "block",
                "type":   "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                },
            })

    return blocks


def _append_blocks(notion: Client, page_id: str, blocks: list[dict]) -> None:
    """Append blocks in batches of 100 (Notion API limit)."""
    for i in range(0, len(blocks), 100):
        batch = blocks[i : i + 100]
        notion.blocks.children.append(block_id=page_id, children=batch)


def _extract_page_title(page: dict) -> str:
    """Pull the title text from a page object."""
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            title_arr = prop.get("title", [])
            if title_arr:
                return title_arr[0].get("plain_text", "Untitled")
    return "Untitled"