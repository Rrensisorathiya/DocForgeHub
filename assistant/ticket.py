# assistant/ticket.py
import os, requests
from utils.logger import setup_logger

logger = setup_logger(__name__)

NOTION_TOKEN    = os.getenv("NOTION_TOKEN", "")
NOTION_TICKET_DB = os.getenv("NOTION_TICKET_DATABASE_ID",
                              os.getenv("NOTION_DATABASE_ID", ""))
NOTION_API      = "https://api.notion.com/v1"
NOTION_VERSION  = "2022-06-28"

def _headers():
    return {
        "Authorization":  f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type":   "application/json",
    }

def create_notion_ticket(
    question: str,
    priority: str,
    department: str,
    owner: str,
    thread_id: str,
    evidence_score: float,
    sources_tried: list,
    conversation_summary: str,
) -> tuple:
    """
    Create a Notion support ticket page.
    Returns (page_id, notion_url).
    """
    db_id = NOTION_TICKET_DB.replace("-", "").strip()
    if not db_id or not NOTION_TOKEN:
        raise ValueError("NOTION_TOKEN or NOTION_TICKET_DATABASE_ID missing")

    # Truncate question for title
    title = question[:80] + ("…" if len(question) > 80 else "")
    sources_text = ", ".join(sources_tried[:3]) if sources_tried else "None"

    properties = {
        "Title": {
            "title": [{"text": {"content": title}}]
        },
        "Status": {
            "select": {"name": "Open"}
        },
        "Priority": {
            "select": {"name": priority.title()}
        },
        "Department": {
            "select": {"name": department or "General"}
        },
        "Assigned To": {
            "rich_text": [{"text": {"content": owner}}]
        },
        "Thread ID": {
            "rich_text": [{"text": {"content": thread_id}}]
        },
        "Evidence Score": {
            "number": round(float(evidence_score), 3)
        },
        "Sources Tried": {
            "rich_text": [{"text": {"content": sources_text[:200]}}]
        },
    }

    # Page body blocks
    children = [
        {
            "object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text",
                "text": {"content": "Full Question"}}]}
        },
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text",
                "text": {"content": question}}]}
        },
        {
            "object": "block", "type": "divider", "divider": {}
        },
        {
            "object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text",
                "text": {"content": "Conversation Summary"}}]}
        },
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text",
                "text": {"content": conversation_summary[:2000]}}]}
        },
        {
            "object": "block", "type": "divider", "divider": {}
        },
        {
            "object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text",
                "text": {"content": "Sources Attempted"}}]}
        },
    ]

    for src in sources_tried:
        children.append({
            "object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"type": "text",
                "text": {"content": src}}]}
        })

    children.append({
        "object": "block", "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {
                "content": f"Evidence score: {evidence_score:.3f} (threshold: 0.45) — insufficient to answer"
            }}],
            "icon": {"type": "emoji", "emoji": "⚠️"},
            "color": "yellow_background",
        }
    })

    payload = {
        "parent":     {"database_id": db_id},
        "properties": properties,
        "children":   children,
    }

    r = requests.post(
        f"{NOTION_API}/pages",
        headers=_headers(),
        json=payload,
        timeout=20,
    )

    if r.status_code != 200:
        raise Exception(f"Notion ticket failed: {r.status_code} {r.text[:300]}")

    page_id    = r.json()["id"]
    notion_url = f"https://www.notion.so/{page_id.replace('-','')}"
    logger.info(f"Notion ticket created: {page_id}")
    return page_id, notion_url


def update_ticket_status(notion_page_id: str, status: str):
    """Update ticket status in Notion: Open → In Progress → Resolved → Closed."""
    r = requests.patch(
        f"{NOTION_API}/pages/{notion_page_id}",
        headers=_headers(),
        json={"properties": {"Status": {"select": {"name": status}}}},
        timeout=15,
    )
    if r.status_code != 200:
        raise Exception(f"Status update failed: {r.text[:200]}")
    return True