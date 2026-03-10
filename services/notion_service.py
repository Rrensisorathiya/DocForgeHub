"""
Notion Integration Service
──────────────────────────
Features:
  - Publishes FULL documents — every section, every table, every paragraph
  - Flat readable pages: headings + content directly on page, no toggles
  - Full markdown TABLE support via Notion's two-step API:
      Step 1: append empty table shell → get block_id
      Step 2: append table_row children to that block_id
  - HTML table fallback: converts <table> HTML to markdown before parsing
  - Rate-limit aware with exponential backoff
  - Smart block parser: h1/h2/h3, bullets, numbered, quotes, dividers, tables, paragraphs
  - Full metadata: type, industry, version, tags, created_by, status, source
"""

import re
import time
import logging
from typing import Optional, Callable
from notion_client import Client
from notion_client.errors import APIResponseError

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

MAX_BLOCK_CHARS     = 2000
MAX_CHILDREN_BATCH  = 100
SECTION_BLOCK_LIMIT = 80
RATE_LIMIT_RETRIES  = 5
RATE_LIMIT_BACKOFF  = 2.0


# ─────────────────────────────────────────────
# Client + Rate-limit wrapper
# ─────────────────────────────────────────────

def _get_client(token: str) -> Client:
    return Client(auth=token)


def _call(fn, *args, **kwargs):
    """Retry on 429 with exponential backoff."""
    delay = RATE_LIMIT_BACKOFF
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except APIResponseError as e:
            if e.status == 429 and attempt < RATE_LIMIT_RETRIES:
                logger.warning(f"Rate limited. Waiting {delay:.1f}s (attempt {attempt+1})...")
                time.sleep(delay)
                delay *= 2
            else:
                raise


# ─────────────────────────────────────────────
# 1. Test Connection
# ─────────────────────────────────────────────

def test_notion_connection(token: str, database_id: str) -> dict:
    try:
        notion    = _get_client(token)
        db        = _call(notion.databases.retrieve, database_id=database_id)
        title_arr = db.get("title", [])
        db_name   = title_arr[0]["plain_text"] if title_arr else "Untitled"
        return {
            "success":       True,
            "database_name": db_name,
            "properties":    list(db.get("properties", {}).keys()),
        }
    except APIResponseError as e:
        return {"success": False, "error": _map_error(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────
# 2. Publish Document
# ─────────────────────────────────────────────

def publish_document_to_notion(
    token:              str,
    database_id:        str,
    title:              str,
    content:            str,
    doc_type:           Optional[str]       = None,
    industry:           Optional[str]       = None,
    version:            Optional[str]       = None,
    tags:               Optional[list[str]] = None,
    created_by:         Optional[str]       = None,
    status:             Optional[str]       = None,
    source_template_id: Optional[str]       = None,
    source_prompts:     Optional[str]       = None,
    extra_properties:   Optional[dict]      = None,
    on_progress:        Optional[Callable]  = None,
) -> dict:
    """
    Publish a full document to Notion as a flat readable page.

    Content is normalized before parsing — HTML tables, escaped markdown,
    and other LLM output quirks are cleaned up so nothing is lost.

    Every section is appended as: ## Heading → content blocks → divider.
    Tables are handled via Notion's two-step API (shell + rows).
    """
    try:
        notion = _get_client(token)

        # ── Normalize content ─────────────────────────────────────────
        content = _normalize_content(content)

        # ── DB schema ─────────────────────────────────────────────────
        db         = _call(notion.databases.retrieve, database_id=database_id)
        db_props   = db.get("properties", {})
        title_prop = _find_title_property(db)

        # ── Properties ────────────────────────────────────────────────
        properties: dict = {
            title_prop: {"title": [{"text": {"content": title[:2000]}}]}
        }

        def _sel(col, val):
            if val and col in db_props:
                properties[col] = {"select": {"name": str(val)[:100]}}

        def _txt(col, val):
            if val and col in db_props:
                properties[col] = {"rich_text": [{"text": {"content": str(val)[:2000]}}]}

        def _multi(col, vals):
            if vals and col in db_props:
                properties[col] = {"multi_select": [{"name": t[:100]} for t in vals]}

        _sel("Status",   status)
        _sel("Type",     doc_type)
        _sel("Industry", industry)
        _sel("Version",  version)
        _multi("Tags", tags)
        _txt("Created By",         created_by)
        _txt("Source Template ID", source_template_id)

        if extra_properties:
            properties.update(extra_properties)

        # ── Split into sections ───────────────────────────────────────
        sections = _split_into_sections(content)
        total    = len(sections)
        logger.info(f"Document split into {total} sections for '{title}'")

        # ── Create page with TOC only ─────────────────────────────────
        initial_children: list[dict] = []

        if source_prompts or source_template_id:
            info_lines = []
            if source_template_id:
                info_lines.append(f"Template ID: {source_template_id}")
            if source_prompts:
                info_lines.append(f"Prompts: {source_prompts[:400]}")
            initial_children.append(_callout_block("📎 Source Info", "\n".join(info_lines)))

        initial_children.append(_callout_block(
            "📄 Table of Contents",
            "\n".join(f"  {i+1}. {s['label']}" for i, s in enumerate(sections)),
        ))

        response = _call(
            notion.pages.create,
            parent={"database_id": database_id},
            properties=properties,
            children=initial_children,
        )
        page_id  = response["id"]
        page_url = response.get("url", "")
        logger.info(f"Page created: {page_id} — appending {total} sections")

        # ── Append all sections ───────────────────────────────────────
        for i, section in enumerate(sections, start=1):
            flat_blocks = (
                [_heading_block(section["label"], 2)]
                + section["blocks"]
                + [{"object": "block", "type": "divider", "divider": {}}]
            )
            _append_blocks_smart(notion, page_id, flat_blocks)

            logger.info(f"  ✓ Section {i}/{total}: '{section['label']}'")
            if on_progress:
                on_progress(i, total, section["label"])
            if i < total:
                time.sleep(0.35)

        logger.info(f"Publish complete: {total} sections → {page_url}")
        return {
            "success":          True,
            "page_id":          page_id,
            "page_url":         page_url,
            "sections_written": total,
        }

    except APIResponseError as e:
        msg = _map_error(e)
        logger.error(f"Notion API error: {msg}")
        return {"success": False, "error": msg}
    except Exception as e:
        logger.exception("Unexpected error during Notion publish")
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────
# 3. List Pages
# ─────────────────────────────────────────────

def list_notion_pages(token: str, database_id: str, limit: int = 20) -> dict:
    try:
        notion   = _get_client(token)
        response = _call(
            notion.databases.query,
            database_id=database_id,
            page_size=limit,
            sorts=[{"timestamp": "created_time", "direction": "descending"}],
        )
        pages = [
            {
                "id":         p["id"],
                "title":      _extract_title(p),
                "url":        p.get("url", ""),
                "created_at": p.get("created_time", ""),
            }
            for p in response.get("results", [])
        ]
        return {"success": True, "pages": pages}
    except APIResponseError as e:
        return {"success": False, "error": _map_error(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────
# Content Normalizer
# Cleans LLM output before parsing so nothing is lost.
# Handles: HTML tables, escaped chars, smart quotes, etc.
# ─────────────────────────────────────────────

def _normalize_content(text: str) -> str:
    """
    Normalize raw LLM / template content into clean markdown.

    1. Convert HTML <table> blocks to markdown pipe tables
    2. Convert HTML <br> to newlines
    3. Strip remaining HTML tags
    4. Fix escaped markdown sequences
    5. Normalize smart quotes and dashes
    """
    if not text:
        return text

    # ── 1. Convert HTML tables → markdown ────────────────────────────
    text = _html_tables_to_markdown(text)

    # ── 2. HTML line breaks → newlines ───────────────────────────────
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    # ── 3. Strip remaining HTML tags ─────────────────────────────────
    text = re.sub(r"<[^>]+>", "", text)

    # ── 4. Decode HTML entities ───────────────────────────────────────
    text = text.replace("&amp;",  "&")
    text = text.replace("&lt;",   "<")
    text = text.replace("&gt;",   ">")
    text = text.replace("&nbsp;", " ")
    text = text.replace("&#39;",  "'")
    text = text.replace("&quot;", '"')

    # ── 5. Normalize smart quotes / dashes ────────────────────────────
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "--")

    # ── 6. Remove excessive blank lines (max 2 consecutive) ──────────
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _html_tables_to_markdown(text: str) -> str:
    """Convert all HTML <table>...</table> blocks to markdown pipe tables."""

    def convert_table(match):
        html = match.group(0)
        rows = []

        # Extract all rows
        for row_match in re.finditer(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE):
            row_html = row_match.group(1)
            cells = []
            # Match both <th> and <td>
            for cell_match in re.finditer(r"<t[hd][^>]*>(.*?)</t[hd]>", row_html, re.DOTALL | re.IGNORECASE):
                cell_text = re.sub(r"<[^>]+>", "", cell_match.group(1))  # strip inner tags
                cell_text = cell_text.replace("\n", " ").strip()
                cells.append(cell_text)
            if cells:
                rows.append(cells)

        if not rows:
            return ""

        col_count = max(len(r) for r in rows)
        padded    = [r + [""] * (col_count - len(r)) for r in rows]

        md_lines = []
        md_lines.append("| " + " | ".join(padded[0]) + " |")
        md_lines.append("| " + " | ".join(["---"] * col_count) + " |")
        for row in padded[1:]:
            md_lines.append("| " + " | ".join(row) + " |")

        return "\n".join(md_lines) + "\n"

    return re.sub(r"<table[^>]*>.*?</table>", convert_table, text, flags=re.DOTALL | re.IGNORECASE)


# ─────────────────────────────────────────────
# Smart Block Appender
#
# Notion table API requires TWO separate calls:
#   Call 1 → append empty table shell → returns table block_id
#   Call 2 → append table_row blocks to that table block_id
#
# All non-table blocks are batched (up to MAX_CHILDREN_BATCH per call).
# ─────────────────────────────────────────────

def _append_blocks_smart(notion: Client, page_id: str, blocks: list[dict]):
    batch: list[dict] = []

    def flush_batch():
        if not batch:
            return
        _call(notion.blocks.children.append, block_id=page_id, children=list(batch))
        batch.clear()

    for block in blocks:
        if block.get("type") == "table":
            flush_batch()  # send pending normal blocks first

            rows       = block.pop("_rows")
            col_count  = block["table"]["table_width"]
            has_header = block["table"]["has_column_header"]

            # Step 1: Create empty table shell
            table_shell = {
                "object": "block",
                "type":   "table",
                "table": {
                    "table_width":       col_count,
                    "has_column_header": has_header,
                    "has_row_header":    False,
                },
            }
            resp           = _call(notion.blocks.children.append, block_id=page_id, children=[table_shell])
            table_block_id = resp["results"][0]["id"]
            logger.info(f"    Table shell created ({col_count} cols, {len(rows)} rows): {table_block_id}")

            # Step 2: Append rows to the table block
            for batch_start in range(0, len(rows), MAX_CHILDREN_BATCH):
                _call(
                    notion.blocks.children.append,
                    block_id=table_block_id,
                    children=rows[batch_start : batch_start + MAX_CHILDREN_BATCH],
                )
            time.sleep(0.2)

        else:
            batch.append(block)
            if len(batch) >= MAX_CHILDREN_BATCH:
                flush_batch()

    flush_batch()


# ─────────────────────────────────────────────
# Section Splitter
# ─────────────────────────────────────────────

def _split_into_sections(text: str) -> list[dict]:
    if not text.strip():
        return [{"label": "Content", "blocks": [_paragraph_block("(empty document)")]}]

    lines         = text.splitlines()
    chunks        = []
    current_label = "Introduction"
    current_lines: list[str] = []

    for line in lines:
        h1 = re.match(r"^#\s+(.*)",  line.strip())
        h2 = re.match(r"^##\s+(.*)", line.strip())
        heading = h1 or h2
        if heading:
            if current_lines:
                chunks.append({"label": current_label, "lines": list(current_lines)})
            current_label = heading.group(1).strip()[:80]
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines or not chunks:
        chunks.append({"label": current_label, "lines": current_lines})

    sections = []
    for chunk in chunks:
        raw    = "\n".join(chunk["lines"])
        blocks = _content_to_blocks(raw)
        if not blocks:
            continue
        if len(blocks) <= SECTION_BLOCK_LIMIT:
            sections.append({"label": chunk["label"], "blocks": blocks})
        else:
            for part_num, i in enumerate(range(0, len(blocks), SECTION_BLOCK_LIMIT), start=1):
                sections.append({
                    "label":  f"{chunk['label']} (Part {part_num})",
                    "blocks": blocks[i : i + SECTION_BLOCK_LIMIT],
                })

    return sections or [{"label": "Content", "blocks": _content_to_blocks(text)}]


# ─────────────────────────────────────────────
# Content → Notion Blocks
# ─────────────────────────────────────────────

def _content_to_blocks(text: str) -> list[dict]:
    """
    Parse clean markdown text into Notion block objects.

    Supported:
      # h1   ## h2   ### h3
      - / * / • bullets
      1. / 1) numbered lists
      > blockquotes
      --- dividers
      | markdown tables |
      plain paragraphs
    """
    if not text.strip():
        return []

    all_blocks: list[dict] = []
    para_buf:   list[str]  = []
    table_buf:  list[str]  = []
    in_table = False

    def flush_para():
        joined = " ".join(para_buf).strip()
        para_buf.clear()
        if not joined:
            return
        for chunk in _chunks(joined):
            all_blocks.append(_paragraph_block(chunk))

    def flush_table():
        if not table_buf:
            return
        tbl = _build_table_block(list(table_buf))
        if tbl:
            all_blocks.append(tbl)
        table_buf.clear()

    for line in text.splitlines():
        s = line.strip()

        # ── Table detection ──────────────────────────────────────────
        if s.startswith("|") and "|" in s[1:]:
            if not in_table:
                flush_para()
                in_table = True
            table_buf.append(s)
            continue
        else:
            if in_table:
                flush_table()
                in_table = False

        if not s:
            flush_para()
            continue

        # Headings
        h3 = re.match(r"^###\s+(.*)", s)
        h2 = re.match(r"^##\s+(.*)",  s)
        h1 = re.match(r"^#\s+(.*)",   s)
        if h3: flush_para(); all_blocks.append(_heading_block(h3.group(1), 3)); continue
        if h2: flush_para(); all_blocks.append(_heading_block(h2.group(1), 2)); continue
        if h1: flush_para(); all_blocks.append(_heading_block(h1.group(1), 1)); continue

        # Bullet list
        bullet = re.match(r"^[-*•]\s+(.*)", s)
        if bullet:
            flush_para()
            for c in _chunks(bullet.group(1)):
                all_blocks.append(_bullet_block(c))
            continue

        # Numbered list
        numbered = re.match(r"^\d+[.)]\s+(.*)", s)
        if numbered:
            flush_para()
            for c in _chunks(numbered.group(1)):
                all_blocks.append(_numbered_block(c))
            continue

        # Blockquote
        quote = re.match(r"^>\s+(.*)", s)
        if quote:
            flush_para()
            all_blocks.append(_quote_block(quote.group(1)[:2000]))
            continue

        # Divider
        if re.match(r"^[-_*]{3,}$", s):
            flush_para()
            all_blocks.append({"object": "block", "type": "divider", "divider": {}})
            continue

        para_buf.append(s)

    # Flush remaining buffers
    if in_table:
        flush_table()
    flush_para()

    return all_blocks


def _build_table_block(table_lines: list[str]) -> Optional[dict]:
    """
    Build a table block from markdown table lines.

    Rows are stored under internal key "_rows" — NOT sent to Notion directly.
    _append_blocks_smart reads "_rows" and uses the two-step table API.
    """
    rows = []
    for line in table_lines:
        s = line.strip()
        # Skip separator lines: |---|---|
        if re.match(r"^\|[\s\-:|]+\|$", s):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if any(c for c in cells):
            rows.append(cells)

    if not rows:
        return None

    col_count = max(len(r) for r in rows)
    padded    = [r + [""] * (col_count - len(r)) for r in rows]

    notion_rows = []
    for row in padded:
        cells = []
        for cell in row:
            cells.append([{"type": "text", "text": {"content": cell[:2000]}}])
        notion_rows.append({
            "object":    "block",
            "type":      "table_row",
            "table_row": {"cells": cells},
        })

    return {
        "object": "block",
        "type":   "table",
        "_rows":  notion_rows,      # ← internal staging key
        "table": {
            "table_width":       col_count,
            "has_column_header": True,
            "has_row_header":    False,
        },
    }


# ─────────────────────────────────────────────
# Block Constructors
# ─────────────────────────────────────────────

def _chunks(text: str) -> list[str]:
    return [text[i:i + MAX_BLOCK_CHARS] for i in range(0, max(len(text), 1), MAX_BLOCK_CHARS)]

def _rt(content: str) -> list[dict]:
    return [{"type": "text", "text": {"content": content}}]

def _paragraph_block(content: str) -> dict:
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": _rt(content)}}

def _heading_block(content: str, level: int) -> dict:
    t = f"heading_{level}"
    return {"object": "block", "type": t, t: {"rich_text": _rt(content[:2000])}}

def _bullet_block(content: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": _rt(content)}}

def _numbered_block(content: str) -> dict:
    return {"object": "block", "type": "numbered_list_item",
            "numbered_list_item": {"rich_text": _rt(content)}}

def _quote_block(content: str) -> dict:
    return {"object": "block", "type": "quote",
            "quote": {"rich_text": _rt(content)}}

def _callout_block(title: str, body: str) -> dict:
    return {
        "object": "block", "type": "callout",
        "callout": {
            "rich_text": _rt(f"{title}\n{body}"[:2000]),
            "icon":      {"type": "emoji", "emoji": "📎"},
            "color":     "gray_background",
        },
    }


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _find_title_property(db: dict) -> str:
    for name, prop in db.get("properties", {}).items():
        if prop.get("type") == "title":
            return name
    return "Name"

def _extract_title(page: dict) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            arr = prop.get("title", [])
            if arr:
                return arr[0].get("plain_text", "Untitled")
    return "Untitled"

def _map_error(e: APIResponseError) -> str:
    return {
        "unauthorized":        "Invalid integration token.",
        "object_not_found":    "Database not found — share it with your integration.",
        "restricted_resource": "Integration has no access to this database.",
        "validation_error":    f"Notion validation error: {e.message}",
        "rate_limited":        "Rate limited — please retry in a moment.",
    }.get(e.code, f"Notion API error ({e.code}): {e.message}")
# """
# Notion Integration Service
# Handles all communication with the Notion API:
#   - Connection testing
#   - Publishing documents as Notion pages
#   - Fetching database schema (column names)
# """

# import logging
# from typing import Optional
# from notion_client import Client
# from notion_client.errors import APIResponseError

# logger = logging.getLogger(__name__)


# # ─────────────────────────────────────────────
# # Helper: build a Notion client
# # ─────────────────────────────────────────────

# def _get_client(token: str) -> Client:
#     return Client(auth=token)


# # ─────────────────────────────────────────────
# # 1. Test Connection
# # ─────────────────────────────────────────────

# def test_notion_connection(token: str, database_id: str) -> dict:
#     """
#     Verify that the integration token is valid and the database is accessible.

#     Returns:
#         {
#             "success": True,
#             "database_name": "My DB",
#             "properties": ["Name", "Status", "Tags", ...]
#         }
#         OR
#         {"success": False, "error": "...reason..."}
#     """
#     try:
#         notion = _get_client(token)
#         db = notion.databases.retrieve(database_id=database_id)

#         # Extract database title
#         title_arr = db.get("title", [])
#         db_name = title_arr[0]["plain_text"] if title_arr else "Untitled Database"

#         # Extract property/column names
#         properties = list(db.get("properties", {}).keys())

#         logger.info(f"Notion connection successful. DB: '{db_name}', Properties: {properties}")
#         return {
#             "success": True,
#             "database_name": db_name,
#             "properties": properties,
#         }

#     except APIResponseError as e:
#         error_map = {
#             "unauthorized":       "Invalid integration token. Re-copy it from notion.so/my-integrations.",
#             "object_not_found":   "Database not found. Make sure you shared the database with your integration.",
#             "restricted_resource":"This integration does not have access to the database.",
#         }
#         msg = error_map.get(e.code, f"Notion API error ({e.code}): {e.message}")
#         logger.error(f"Notion API error during test: {msg}")
#         return {"success": False, "error": msg}

#     except Exception as e:
#         logger.exception("Unexpected error during Notion connection test")
#         return {"success": False, "error": str(e)}


# # ─────────────────────────────────────────────
# # 2. Publish Document
# # ─────────────────────────────────────────────

# def publish_document_to_notion(
#     token: str,
#     database_id: str,
#     title: str,
#     content: str,
#     status: Optional[str] = None,
#     tags: Optional[list[str]] = None,
#     extra_properties: Optional[dict] = None,
# ) -> dict:
#     """
#     Create a new page in a Notion database with the given document content.

#     Args:
#         token:            Notion integration secret token.
#         database_id:      Target Notion database ID.
#         title:            Document title → goes into the Title/Name column.
#         content:          Full document text → becomes paragraph blocks on the page.
#         status:           Optional value for a 'Status' select column.
#         tags:             Optional list of tag strings for a 'Tags' multi-select column.
#         extra_properties: Any additional Notion property dicts to merge in.

#     Returns:
#         {"success": True, "page_id": "...", "page_url": "https://notion.so/..."}
#         OR
#         {"success": False, "error": "...reason..."}
#     """
#     try:
#         notion = _get_client(token)

#         # ── Fetch DB to find the real title-column name ──────────────────
#         db = notion.databases.retrieve(database_id=database_id)
#         title_prop_name = _find_title_property(db)

#         # ── Build properties ─────────────────────────────────────────────
#         properties: dict = {
#             title_prop_name: {
#                 "title": [{"text": {"content": title[:2000]}}]
#             }
#         }

#         db_props = db.get("properties", {})

#         if status and "Status" in db_props:
#             properties["Status"] = {"select": {"name": status}}

#         if tags and "Tags" in db_props:
#             properties["Tags"] = {"multi_select": [{"name": t} for t in tags]}

#         if extra_properties:
#             properties.update(extra_properties)

#         # ── Build content blocks ─────────────────────────────────────────
#         children = _text_to_blocks(content)

#         # ── Create the page ──────────────────────────────────────────────
#         response = notion.pages.create(
#             parent={"database_id": database_id},
#             properties=properties,
#             children=children[:100],   # Notion allows max 100 blocks per request
#         )

#         page_id  = response["id"]
#         page_url = response.get("url", "")

#         # If content was long, append remaining blocks
#         if len(children) > 100:
#             _append_blocks(notion, page_id, children[100:])

#         logger.info(f"Published to Notion. Page ID: {page_id}")
#         return {"success": True, "page_id": page_id, "page_url": page_url}

#     except APIResponseError as e:
#         error_map = {
#             "unauthorized":       "Invalid integration token.",
#             "object_not_found":   "Database not found or not shared with integration.",
#             "validation_error":   f"Notion validation error: {e.message} — check your database column names.",
#         }
#         msg = error_map.get(e.code, f"Notion API error ({e.code}): {e.message}")
#         logger.error(f"Notion API error during publish: {msg}")
#         return {"success": False, "error": msg}

#     except Exception as e:
#         logger.exception("Unexpected error during Notion publish")
#         return {"success": False, "error": str(e)}


# # ─────────────────────────────────────────────
# # 3. List Pages (optional helper for frontend)
# # ─────────────────────────────────────────────

# def list_notion_pages(token: str, database_id: str, limit: int = 20) -> dict:
#     """
#     Return recently created pages from the database (for display / confirmation).
#     """
#     try:
#         notion = _get_client(token)
#         response = notion.databases.query(
#             database_id=database_id,
#             page_size=limit,
#             sorts=[{"timestamp": "created_time", "direction": "descending"}],
#         )

#         pages = []
#         for page in response.get("results", []):
#             title = _extract_page_title(page)
#             pages.append({
#                 "id":         page["id"],
#                 "title":      title,
#                 "url":        page.get("url", ""),
#                 "created_at": page.get("created_time", ""),
#             })

#         return {"success": True, "pages": pages}

#     except APIResponseError as e:
#         return {"success": False, "error": f"Notion API error ({e.code}): {e.message}"}
#     except Exception as e:
#         return {"success": False, "error": str(e)}


# # ─────────────────────────────────────────────
# # Private Helpers
# # ─────────────────────────────────────────────

# def _find_title_property(db: dict) -> str:
#     """Return the name of the title-type property in the database."""
#     for name, prop in db.get("properties", {}).items():
#         if prop.get("type") == "title":
#             return name
#     return "Name"   # sensible fallback


# def _text_to_blocks(text: str) -> list[dict]:
#     """
#     Convert a plain-text string into Notion paragraph blocks.
#     Splits on double newlines (paragraphs) and respects Notion's 2000-char block limit.
#     """
#     if not text:
#         return []

#     blocks = []
#     paragraphs = text.split("\n\n") if "\n\n" in text else [text]

#     for para in paragraphs:
#         para = para.strip()
#         if not para:
#             continue
#         # Split into ≤2000-char chunks
#         for i in range(0, len(para), 2000):
#             chunk = para[i : i + 2000]
#             blocks.append({
#                 "object": "block",
#                 "type":   "paragraph",
#                 "paragraph": {
#                     "rich_text": [{"type": "text", "text": {"content": chunk}}]
#                 },
#             })

#     return blocks


# def _append_blocks(notion: Client, page_id: str, blocks: list[dict]) -> None:
#     """Append blocks in batches of 100 (Notion API limit)."""
#     for i in range(0, len(blocks), 100):
#         batch = blocks[i : i + 100]
#         notion.blocks.children.append(block_id=page_id, children=batch)


# def _extract_page_title(page: dict) -> str:
#     """Pull the title text from a page object."""
#     props = page.get("properties", {})
#     for prop in props.values():
#         if prop.get("type") == "title":
#             title_arr = prop.get("title", [])
#             if title_arr:
#                 return title_arr[0].get("plain_text", "Untitled")
#     return "Untitled"