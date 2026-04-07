# rag/ingestion.py
import os, time
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger(__name__)

NOTION_API_URL  = "https://api.notion.com/v1"
NOTION_VERSION  = "2022-06-28"
CHUNK_SIZE      = int(os.getenv("RAG_CHUNK_SIZE", "512"))
CHUNK_OVERLAP   = int(os.getenv("RAG_CHUNK_OVERLAP", "64"))


def _headers(token: str) -> dict:
    return {
        "Authorization":  f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type":   "application/json",
    }


def _get_page_title(page: dict) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            parts = prop.get("title", [])
            if parts:
                return parts[0].get("plain_text", "Untitled")
    return "Untitled"


def _get_select(page: dict, key: str) -> str:
    prop = page.get("properties", {}).get(key, {})
    sel  = prop.get("select")
    return sel.get("name", "") if sel else ""


def _get_rich_text(page: dict, key: str) -> str:
    prop  = page.get("properties", {}).get(key, {})
    parts = prop.get("rich_text", [])
    return parts[0].get("plain_text", "") if parts else ""


def _extract_page_text(page_id: str, token: str) -> str:
    """Fetch all block text from a Notion page (paginated)."""
    import requests
    blocks = []
    url    = f"{NOTION_API_URL}/blocks/{page_id}/children"
    cursor = None
    has_more = True

    while has_more:
        params = {"page_size": 100}
        if cursor:
            params["start_cursor"] = cursor
        try:
            r = requests.get(url, headers=_headers(token), params=params, timeout=20)
            if r.status_code != 200:
                logger.warning(f"Block fetch {page_id}: HTTP {r.status_code}")
                break
            data     = r.json()
            has_more = data.get("has_more", False)
            cursor   = data.get("next_cursor")

            for block in data.get("results", []):
                btype   = block.get("type", "")
                content = block.get(btype, {})
                rich    = content.get("rich_text", [])
                text    = " ".join(rt.get("plain_text", "") for rt in rich)
                if text.strip():
                    blocks.append(text.strip())
        except Exception as e:
            logger.error(f"Block fetch error for {page_id}: {e}")
            break

    return "\n".join(blocks)


def ingest_notion_documents(token: str, database_id: str,
                            force_reingest: bool = False) -> dict:
    """
    Fetch all pages from a Notion database, chunk them,
    and store them in ChromaDB.  Uses Redis to skip already-ingested pages.
    """
    import requests
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document
    from rag.vector_store import vector_store
    from cache.redis_service import redis_client

    db_id    = database_id.replace("-", "").strip()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )

    pages_ingested = 0
    chunks_total   = 0
    skipped        = 0
    errors         = []

    has_more = True
    cursor   = None

    while has_more:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor

        try:
            r = requests.post(
                f"{NOTION_API_URL}/databases/{db_id}/query",
                headers=_headers(token),
                json=payload,
                timeout=20,
            )
        except Exception as e:
            logger.error(f"Notion DB query error: {e}")
            break

        if r.status_code != 200:
            msg = f"Notion API error {r.status_code}: {r.text[:200]}"
            logger.error(msg)
            return {"success": False, "message": msg}

        data     = r.json()
        has_more = data.get("has_more", False)
        cursor   = data.get("next_cursor")

        for page in data.get("results", []):
            page_id  = page["id"]
            ingest_k = f"ingested:{page_id}"

            # skip if already ingested (unless force)
            if not force_reingest and redis_client.get(ingest_k):
                skipped += 1
                continue

            # metadata
            title     = _get_page_title(page)
            dept      = _get_select(page, "Department")
            doc_type  = _get_select(page, "Document Type")
            industry  = _get_select(page, "Industry")
            version   = _get_select(page, "Version")
            company   = _get_rich_text(page, "Company")

            # extract text
            try:
                full_text = _extract_page_text(page_id, token)
            except Exception as e:
                errors.append(f"{page_id}: text extraction failed — {e}")
                continue

            if not full_text.strip():
                logger.debug(f"Page {page_id} ({title}) has no text — skipping")
                continue

            # chunk + build Document objects
            text_chunks = splitter.split_text(full_text)
            docs = []
            for i, chunk in enumerate(text_chunks):
                docs.append(Document(
                    page_content=chunk,
                    metadata={
                        "page_id":     page_id,
                        "doc_title":   title,
                        "department":  dept,
                        "doc_type":    doc_type,
                        "industry":    industry,
                        "version":     version,
                        "company":     company,
                        "block_range": f"{i * CHUNK_SIZE}-{(i + 1) * CHUNK_SIZE}",
                        "source":      f"notion:{page_id}",
                    }
                ))

            if docs:
                try:
                    vector_store.add_documents(docs)
                    chunks_total   += len(docs)
                    pages_ingested += 1
                    # mark in Redis (24 h)
                    redis_client.set(
                        ingest_k,
                        {"title": title, "ingested_at": datetime.now().isoformat()},
                        ttl=86400,
                    )
                    logger.info(f"Ingested '{title}' — {len(docs)} chunks")
                except Exception as e:
                    errors.append(f"{page_id}: ChromaDB write failed — {e}")

            time.sleep(0.1)   # gentle rate-limiting on Notion API

    result = {
        "success":        True,
        "pages_ingested": pages_ingested,
        "chunks_created": chunks_total,
        "skipped":        skipped,
        "errors":         errors,
        "message": (
            f"Ingested {pages_ingested} pages ({chunks_total} chunks). "
            f"Skipped {skipped} already-ingested."
        ),
    }
    logger.info(result["message"])
    return result
# """
# Ingestion Service — Notion → Chunks → VectorStore
# """

# import os
# import re
# import time
# from typing import Optional
# from dotenv import load_dotenv
# from utils.logger import setup_logger
# from rag.vector_store import vector_store
# from cache.redis_service import redis_client

# load_dotenv()
# logger = setup_logger(__name__)

# NOTION_API_URL = "https://api.notion.com/v1"
# NOTION_VERSION = "2022-06-28"
# CHUNK_SIZE     = 500
# CHUNK_OVERLAP  = 50


# def _notion_headers(token: str) -> dict:
#     return {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json",
#         "Notion-Version": NOTION_VERSION,
#     }


# def fetch_notion_pages(token: str, database_id: str) -> list:
#     import requests
#     if not redis_client.check_notion_rate(database_id):
#         logger.warning("Notion rate limit hit — waiting 60s")
#         time.sleep(60)

#     pages    = []
#     has_more = True
#     cursor   = None

#     while has_more:
#         payload = {"page_size": 100}
#         if cursor:
#             payload["start_cursor"] = cursor
#         try:
#             resp = requests.post(
#                 f"{NOTION_API_URL}/databases/{database_id}/query",
#                 headers=_notion_headers(token),
#                 json=payload,
#                 timeout=30,
#             )
#             resp.raise_for_status()
#             data     = resp.json()
#             has_more = data.get("has_more", False)
#             cursor   = data.get("next_cursor")
#             for page in data.get("results", []):
#                 if not page.get("archived", False):
#                     pages.append(page)
#             logger.info(f"Fetched {len(pages)} pages so far...")
#             time.sleep(0.3)
#         except Exception as e:
#             logger.error(f"Notion fetch failed: {e}")
#             break

#     logger.info(f"Total pages fetched: {len(pages)}")
#     return pages


# def fetch_page_content(token: str, page_id: str) -> str:
#     import requests
#     database_id = os.getenv("NOTION_DATABASE_ID", "default")
#     if not redis_client.check_notion_rate(database_id):
#         time.sleep(60)

#     text_parts = []
#     has_more   = True
#     cursor     = None

#     while has_more:
#         params = {"page_size": 100}
#         if cursor:
#             params["start_cursor"] = cursor
#         try:
#             resp = requests.get(
#                 f"{NOTION_API_URL}/blocks/{page_id}/children",
#                 headers=_notion_headers(token),
#                 params=params,
#                 timeout=30,
#             )
#             resp.raise_for_status()
#             data     = resp.json()
#             has_more = data.get("has_more", False)
#             cursor   = data.get("next_cursor")
#             for block in data.get("results", []):
#                 text = _extract_block_text(block)
#                 if text:
#                     text_parts.append(text)
#             time.sleep(0.2)
#         except Exception as e:
#             logger.error(f"Page content fetch failed for {page_id}: {e}")
#             break

#     return "\n".join(text_parts)


# def _extract_block_text(block: dict) -> str:
#     btype   = block.get("type", "")
#     content = block.get(btype, {})
#     if "rich_text" in content:
#         return "".join(rt.get("plain_text", "") for rt in content["rich_text"])
#     if btype == "table_row":
#         cells = content.get("cells", [])
#         return " | ".join(
#             "".join(rt.get("plain_text", "") for rt in cell)
#             for cell in cells
#         )
#     return ""


# def extract_page_metadata(page: dict) -> dict:
#     props = page.get("properties", {})

#     def get_text(prop):
#         if not prop:
#             return ""
#         ptype = prop.get("type", "")
#         if ptype == "title":
#             return "".join(t.get("plain_text", "") for t in prop.get("title", []))
#         if ptype == "rich_text":
#             return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
#         if ptype == "select":
#             return prop.get("select", {}).get("name", "") if prop.get("select") else ""
#         if ptype == "number":
#             return str(prop.get("number", ""))
#         return ""

#     title = ""
#     for prop in props.values():
#         if prop.get("type") == "title":
#             title = get_text(prop)
#             break

#     return {
#         "page_id":    page.get("id", ""),
#         "title":      title,
#         "doc_type":   get_text(props.get("Document Type", {})),
#         "department": get_text(props.get("Department", {})),
#         "industry":   get_text(props.get("Industry", {})),
#         "version":    get_text(props.get("Version", {})) or "v1",
#         "notion_url": page.get("url", ""),
#     }


# def chunk_text(text: str, metadata: dict, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
#     if not text.strip():
#         return []

#     chunks   = []
#     sections = re.split(r'\n(?=#{1,3} )', text)

#     for sec_idx, section in enumerate(sections):
#         if not section.strip():
#             continue
#         lines        = section.strip().split("\n")
#         section_name = lines[0].lstrip("#").strip() if lines else f"Section {sec_idx+1}"
#         section_text = section.strip()
#         words        = section_text.split()

#         if len(words) <= chunk_size:
#             chunk_id = f"{metadata['page_id']}_{sec_idx}_0"
#             chunks.append({
#                 "id":   chunk_id,
#                 "text": section_text,
#                 "metadata": {
#                     **metadata,
#                     "section":   section_name,
#                     "chunk_idx": 0,
#                     "doc_id":    metadata["page_id"],
#                 },
#             })
#         else:
#             start = 0
#             cidx  = 0
#             while start < len(words):
#                 end            = min(start + chunk_size, len(words))
#                 chunk_text_str = " ".join(words[start:end])
#                 chunk_id       = f"{metadata['page_id']}_{sec_idx}_{cidx}"
#                 chunks.append({
#                     "id":   chunk_id,
#                     "text": chunk_text_str,
#                     "metadata": {
#                         **metadata,
#                         "section":   section_name,
#                         "chunk_idx": cidx,
#                         "doc_id":    metadata["page_id"],
#                     },
#                 })
#                 start += chunk_size - overlap
#                 cidx  += 1

#     return chunks


# def ingest_notion_documents(token: str, database_id: str, force_reingest: bool = False) -> dict:
#     logger.info(f"Starting ingestion from Notion DB: {database_id}")

#     pages = fetch_notion_pages(token, database_id)
#     if not pages:
#         return {"success": False, "message": "No pages found", "ingested": 0}

#     total_chunks  = 0
#     total_pages   = 0
#     skipped_pages = 0

#     for page in pages:
#         meta    = extract_page_metadata(page)
#         page_id = meta["page_id"]

#         if not force_reingest:
#             cache_key = f"ingested:{page_id}"
#             if redis_client.get(cache_key):
#                 logger.debug(f"Skipping already ingested: {meta['title']}")
#                 skipped_pages += 1
#                 continue

#         logger.info(f"Ingesting: {meta['title']} ({meta['doc_type']})")
#         content = fetch_page_content(token, page_id)
#         if not content.strip():
#             logger.warning(f"Empty content for: {meta['title']}")
#             continue

#         if force_reingest:
#             vector_store.delete_by_doc_id(page_id)

#         chunks = chunk_text(content, meta)
#         if not chunks:
#             continue

#         added = vector_store.add_chunks(chunks)
#         total_chunks += added
#         total_pages  += 1

#         redis_client.set(f"ingested:{page_id}", {"title": meta["title"]}, ttl=86400)
#         logger.info(f"Ingested {added} chunks for: {meta['title']}")
#         time.sleep(0.3)

#     result = {
#         "success":       True,
#         "total_pages":   total_pages,
#         "skipped_pages": skipped_pages,
#         "total_chunks":  total_chunks,
#         "vector_stats":  vector_store.stats(),
#     }
#     logger.info(f"Ingestion complete: {result}")
#     return result


# def ingest_single_page(token: str, page_id: str, metadata: dict) -> dict:
#     content = fetch_page_content(token, page_id)
#     if not content.strip():
#         return {"success": False, "message": "Empty content"}
#     chunks = chunk_text(content, metadata)
#     added  = vector_store.add_chunks(chunks)
#     return {"success": True, "chunks": added, "title": metadata.get("title", "")}