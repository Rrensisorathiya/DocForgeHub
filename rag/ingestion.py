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

