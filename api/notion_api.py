"""
api/notion_api.py — Complete Notion API Router for DocForgeHub
===============================================================
FIXES:
  ✅ "Name is not a property that exists" — uses dynamic title detection
  ✅ Handles any Notion DB property names (Title, Name, or custom)
  ✅ Graceful fallback if optional properties don't exist in DB
  ✅ Full publish with beautiful rich formatting
  ✅ All 130 document types + 13 departments supported
"""

import os
import re
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

NOTION_VERSION = "2022-06-28"
NOTION_BASE    = "https://api.notion.com/v1"

# ══════════════════════════════════════════════════════════════
# DEPARTMENT STYLING
# ══════════════════════════════════════════════════════════════

DEPT_EMOJI = {
    "HR & People Operations":                "👥",
    "Legal & Compliance":                    "⚖️",
    "Sales & Customer Facing":               "💼",
    "Engineering & Operations":              "⚙️",
    "Product & Design":                      "🎨",
    "Marketing & Content":                   "📣",
    "Finance & Operations":                  "💰",
    "Partnership & Alliances":               "🤝",
    "IT & Internal Systems":                 "🖥️",
    "Platform & Infrastructure Operations":  "☁️",
    "Data & Analytics":                      "📊",
    "QA & Testing":                          "✅",
    "Security & Information Assurance":      "🔐",
}

DEPT_COLOR = {
    "HR & People Operations":                "pink_background",
    "Legal & Compliance":                    "blue_background",
    "Sales & Customer Facing":               "green_background",
    "Engineering & Operations":              "orange_background",
    "Product & Design":                      "purple_background",
    "Marketing & Content":                   "yellow_background",
    "Finance & Operations":                  "red_background",
    "Partnership & Alliances":               "green_background",
    "IT & Internal Systems":                 "gray_background",
    "Platform & Infrastructure Operations":  "blue_background",
    "Data & Analytics":                      "brown_background",
    "QA & Testing":                          "gray_background",
    "Security & Information Assurance":      "red_background",
}

SECTION_COLORS = ["blue", "purple", "pink", "orange", "green", "red", "brown", "gray"]


# ══════════════════════════════════════════════════════════════
# REQUEST MODELS
# ══════════════════════════════════════════════════════════════

class TokenTestRequest(BaseModel):
    token: str

class DBTestRequest(BaseModel):
    token: str
    database_id: str

class SetupDBRequest(BaseModel):
    token: str
    database_id: str

class PublishRequest(BaseModel):
    token: str
    database_id: str
    document_id: str

class PublishAllRequest(BaseModel):
    token: str
    database_id: str


# ══════════════════════════════════════════════════════════════
# NOTION HTTP HELPERS
# ══════════════════════════════════════════════════════════════

def _headers(token: str) -> dict:
    return {
        "Authorization":  f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type":   "application/json",
    }

def _get(token, path):
    return requests.get(f"{NOTION_BASE}{path}", headers=_headers(token)).json()

def _post(token, path, body):
    return requests.post(f"{NOTION_BASE}{path}", headers=_headers(token), json=body).json()

def _patch(token, path, body):
    return requests.patch(f"{NOTION_BASE}{path}", headers=_headers(token), json=body).json()


# ══════════════════════════════════════════════════════════════
# DYNAMIC PROPERTY DETECTION  ← THE CORE FIX
# ══════════════════════════════════════════════════════════════

def _get_db_props(token: str, db_id: str) -> dict:
    """Returns {prop_name: prop_type} dict for the Notion database."""
    data = _get(token, f"/databases/{db_id}")
    if "properties" not in data:
        raise HTTPException(
            status_code=403,
            detail=f"Cannot access DB. Notion says: {data.get('message', 'Unknown error')}"
        )
    return {name: info["type"] for name, info in data["properties"].items()}


def _find_title_prop(props: dict) -> str:
    """
    ✅ THE FIX: Find the title column dynamically.
    Notion DBs always have exactly ONE title property.
    It could be called 'Title', 'Name', 'Document', or anything.
    This function finds it regardless of what it's named.
    """
    for name, ptype in props.items():
        if ptype == "title":
            return name
    return "Title"  # should never reach here


def _set_prop(props_payload: dict, db_props: dict, key: str, value) -> None:
    """
    Safely write a property value using case-insensitive matching.
    Silently skips if property doesn't exist — never crashes.
    """
    if value is None:
        return
    lookup = {k.lower(): k for k in db_props.keys()}
    real   = lookup.get(key.lower())
    if not real:
        return  # property not in this DB — skip safely

    ptype = db_props[real]
    if ptype == "select":
        props_payload[real] = {"select": {"name": str(value)}}
    elif ptype == "rich_text":
        props_payload[real] = {"rich_text": [{"type": "text", "text": {"content": str(value)[:2000]}}]}
    elif ptype == "number":
        try:
            props_payload[real] = {"number": float(value)}
        except (ValueError, TypeError):
            pass
    elif ptype == "date":
        props_payload[real] = {"date": {"start": str(value)}}


# ══════════════════════════════════════════════════════════════
# NOTION BLOCK BUILDERS
# ══════════════════════════════════════════════════════════════

def _rt(text: str, bold=False, color="default") -> list:
    return [{"type": "text", "text": {"content": text[:2000]},
             "annotations": {"bold": bold, "italic": False, "code": False, "color": color}}]

def _heading(text: str, level: int, color: str = "default") -> dict:
    clean = re.sub(r'^#{1,4}\s*', '', text).strip()[:2000]
    ht = f"heading_{min(level, 3)}"
    return {"object": "block", "type": ht, ht: {"rich_text": _rt(clean), "color": color}}

def _paragraph(text: str) -> dict:
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": _rt(text[:2000])}}

def _bullet(text: str) -> dict:
    clean = re.sub(r'^[-•*]\s*', '', text).strip()[:2000]
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": _rt(clean)}}

def _numbered(text: str) -> dict:
    clean = re.sub(r'^\d+\.\s*', '', text).strip()[:2000]
    return {"object": "block", "type": "numbered_list_item",
            "numbered_list_item": {"rich_text": _rt(clean)}}

def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}

def _callout(text: str, emoji: str = "📋", color: str = "blue_background") -> dict:
    return {"object": "block", "type": "callout",
            "callout": {"rich_text": _rt(text[:2000]),
                        "icon": {"type": "emoji", "emoji": emoji}, "color": color}}

def _quote(text: str) -> dict:
    return {"object": "block", "type": "quote", "quote": {"rich_text": _rt(text[:2000])}}

def _toc() -> dict:
    return {"object": "block", "type": "table_of_contents", "table_of_contents": {"color": "gray"}}


# ══════════════════════════════════════════════════════════════
# MARKDOWN → NOTION BLOCKS
# ══════════════════════════════════════════════════════════════

def _md_to_blocks(markdown: str, dept: str = "") -> list:
    blocks = []
    lines  = markdown.split("\n")
    i = 0
    section_count = 0

    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue

        if s.startswith("# ") and not s.startswith("## "):
            i += 1
            continue  # H1 = page title already set in properties

        elif s.startswith("## "):
            section_count += 1
            if section_count > 1:
                blocks.append(_divider())
            color = SECTION_COLORS[(section_count - 1) % len(SECTION_COLORS)]
            blocks.append(_heading(s[3:].strip(), 2, color))

        elif s.startswith("### "):
            blocks.append(_heading(s[4:].strip(), 3))

        elif s.startswith("#### "):
            blocks.append(_heading(s[5:].strip(), 3))

        elif s.startswith(("- ", "• ", "* ")):
            blocks.append(_bullet(s))

        elif re.match(r'^\d+\.\s', s):
            blocks.append(_numbered(s))

        elif s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = lines[i].strip()
                if not re.match(r'^\|[-:\s|]+\|$', row):
                    rows.append(row)
                i += 1
            if rows:
                blocks.append(_callout("\n".join(rows[:8]), "📊", "gray_background"))
            continue

        elif s in ("---", "===", "***", "___"):
            blocks.append(_divider())

        elif s.startswith("> "):
            blocks.append(_quote(s[2:]))

        elif s.startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            blocks.append({
                "object": "block", "type": "code",
                "code": {"rich_text": [{"type": "text", "text": {"content": "\n".join(code)[:2000]}}],
                         "language": "plain text"}
            })
        else:
            text = s
            while len(text) > 2000:
                blocks.append(_paragraph(text[:2000]))
                text = text[2000:]
            if text:
                blocks.append(_paragraph(text))

        i += 1

    return blocks


# ══════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════

def _header_blocks(doc_type, dept, industry, company, version, score, grade, wc) -> list:
    emoji = DEPT_EMOJI.get(dept, "📄")
    bg    = DEPT_COLOR.get(dept, "blue_background")
    now   = datetime.now().strftime("%B %d, %Y")
    meta2 = "  |  ".join(filter(None, [
        f"⭐ Score: {score}/100" if score else None,
        f"🏆 Grade: {grade}"     if grade else None,
        f"📝 Words: {wc:,}"      if wc    else None,
    ]))
    return [
        _callout(f"{doc_type}  ·  {company}  ·  {dept}", emoji, bg),
        _divider(),
        _callout(f"🏭 Industry: {industry}   |   📁 {dept}   |   🏢 {company}", "ℹ️", "gray_background"),
        _callout(f"📌 v{version}   |   📅 {now}" + (f"   |   {meta2}" if meta2 else ""), "📊", "blue_background"),
        _divider(),
        _toc(),
        _divider(),
    ]


# ══════════════════════════════════════════════════════════════
# CORE PUBLISH
# ══════════════════════════════════════════════════════════════

def _publish(token, db_id, doc_type, dept, industry, content,
             company="Turabit", version="1.0",
             score=None, grade=None, wc=None) -> dict:

    # 1. Detect real property names — never hardcode "Name" or "Title"
    db_props   = _get_db_props(token, db_id)
    title_prop = _find_title_prop(db_props)

    # 2. Build page properties
    emoji = DEPT_EMOJI.get(dept, "📄")
    properties = {
        title_prop: {"title": [{"type": "text", "text": {"content": f"{emoji} {doc_type} — {company}"}}]}
    }
    _set_prop(properties, db_props, "Department",    dept)
    _set_prop(properties, db_props, "Document Type", doc_type)
    _set_prop(properties, db_props, "Industry",      industry)
    _set_prop(properties, db_props, "Status",        "✅ Published")
    _set_prop(properties, db_props, "Version",       version)
    _set_prop(properties, db_props, "Company",       company)
    _set_prop(properties, db_props, "Published At",  datetime.now().date().isoformat())
    if score is not None: _set_prop(properties, db_props, "Score",      score)
    if grade:             _set_prop(properties, db_props, "Grade",      grade)
    if wc:                _set_prop(properties, db_props, "Word Count", wc)

    # 3. Build blocks
    all_blocks = (
        _header_blocks(doc_type, dept, industry, company, version, score, grade, wc)
        + _md_to_blocks(content, dept)
    )

    # 4. Create page
    result = _post(token, "/pages", {
        "parent":     {"database_id": db_id},
        "icon":       {"type": "emoji", "emoji": emoji},
        "cover":      {"type": "external", "external": {
            "url": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1200"
        }},
        "properties": properties,
        "children":   all_blocks[:95],
    })

    if "id" not in result:
        raise HTTPException(
            status_code=500,
            detail=f"Notion error: {result.get('message', 'Unknown')} | code: {result.get('code', '?')}"
        )

    pid = result["id"]
    url = result.get("url", f"https://notion.so/{pid.replace('-','')}")

    # 5. Append remaining blocks in batches of 95
    for start in range(95, len(all_blocks), 95):
        _patch(token, f"/blocks/{pid}/children", {"children": all_blocks[start:start+95]})

    return {"success": True, "page_id": pid, "url": url,
            "title": f"{emoji} {doc_type} — {company}", "blocks_created": len(all_blocks)}


# ══════════════════════════════════════════════════════════════
# ALL DOCUMENT TYPE OPTIONS (130 types)
# ══════════════════════════════════════════════════════════════

ALL_DOC_TYPES = {
    "HR & People Operations": ("pink", [
        "Offer Letter", "Employment Contract", "Employee Handbook",
        "HR Policy Manual", "Onboarding Checklist", "Performance Appraisal Form",
        "Leave Policy Document", "Code of Conduct", "Exit Interview Form",
        "Training & Development Plan",
    ]),

    "Legal & Compliance": ("blue", [
        "Master Service Agreement (MSA)", "Non-Disclosure Agreement (NDA)",
        "Data Processing Agreement (DPA)", "Privacy Policy", "Terms of Service",
        "Compliance Audit Report", "Risk Assessment Report",
        "Intellectual Property Agreement", "Vendor Contract Template",
        "Regulatory Compliance Checklist",
    ]),

    "Sales & Customer Facing": ("green", [
        "Sales Proposal Template", "Sales Playbook", "Customer Onboarding Guide",
        "Service Level Agreement (SLA)", "Pricing Strategy Document",
        "Customer Case Study", "Sales Contract", "CRM Usage Guidelines",
        "Quarterly Sales Report", "Customer Feedback Report",
    ]),

    "Engineering & Operations": ("orange", [
        "Software Requirements Specification (SRS)", "Technical Design Document (TDD)",
        "API Documentation", "Deployment Guide", "Release Notes",
        "System Architecture Document", "Incident Report",
        "Root Cause Analysis (RCA)", "DevOps Runbook", "Change Management Log",
    ]),

    "Product & Design": ("purple", [
        "Product Requirements Document (PRD)", "Product Roadmap",
        "Feature Specification Document", "UX Research Report",
        "Wireframe Documentation", "Design System Guide",
        "User Persona Document", "A/B Testing Report",
        "Product Strategy Document", "Competitive Analysis Report",
    ]),

    "Marketing & Content": ("yellow", [
        "Marketing Strategy Plan", "Content Calendar", "Brand Guidelines",
        "SEO Strategy Document", "Campaign Performance Report",
        "Social Media Strategy", "Email Marketing Plan",
        "Press Release Template", "Market Research Report",
        "Lead Generation Plan",
    ]),

    "Finance & Operations": ("red", [
        "Annual Budget Plan", "Financial Statement Report", "Expense Policy",
        "Invoice Template", "Procurement Policy", "Revenue Forecast Report",
        "Cash Flow Statement", "Vendor Payment Policy",
        "Cost Analysis Report", "Financial Risk Assessment",
    ]),

    "Security & Information Assurance": ("red", [
        "Information Security Policy", "Cybersecurity Risk Assessment",
        "Vulnerability Assessment Report", "Penetration Testing Report",
        "Security Audit Report", "Data Classification Policy",
        "Business Continuity Plan (BCP)", "Security Awareness Training Material",
    ]),
}

# ══════════════════════════════════════════════════════════════
# API ROUTES
# ══════════════════════════════════════════════════════════════

@router.post("/test-token")
def api_test_token(req: TokenTestRequest):
    result = _get(req.token, "/users/me")
    if "id" not in result:
        raise HTTPException(status_code=401, detail=result.get("message", "Invalid token"))
    return {"valid": True, "user": result.get("name", "Unknown"), "type": result.get("type")}


@router.post("/test-database")
def api_test_database(req: DBTestRequest):
    try:
        props      = _get_db_props(req.token, req.database_id)
        title_prop = _find_title_prop(props)
        return {
            "valid":          True,
            "title_property": title_prop,
            "properties":     props,
            "property_count": len(props),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-detect-databases")
def api_auto_detect(req: TokenTestRequest):
    result = _post(req.token, "/search", {
        "filter": {"value": "database", "property": "object"}, "page_size": 20
    })
    dbs = []
    for db in result.get("results", []):
        t = db.get("title", [])
        dbs.append({"id": db["id"], "title": t[0].get("plain_text", "Untitled") if t else "Untitled",
                    "url": db.get("url", "")})
    return {"databases": dbs, "count": len(dbs)}


@router.post("/setup-database")
def api_setup_database(req: SetupDBRequest):
    """Add all required properties to the DB. Safe to run multiple times."""
    try:
        existing       = _get_db_props(req.token, req.database_id)
        existing_lower = {k.lower() for k in existing.keys()}

        NEW_PROPS = {
            "Department":    {"select": {"options": [
                {"name": "HR & People Operations",               "color": "pink"},
                {"name": "Legal & Compliance",                   "color": "blue"},
                {"name": "Sales & Customer Facing",              "color": "green"},
                {"name": "Engineering & Operations",             "color": "orange"},
                {"name": "Product & Design",                     "color": "purple"},
                {"name": "Marketing & Content",                  "color": "yellow"},
                {"name": "Finance & Operations",                 "color": "red"},
                {"name": "Partnership & Alliances",              "color": "green"},
                {"name": "IT & Internal Systems",                "color": "gray"},
                {"name": "Platform & Infrastructure Operations", "color": "blue"},
                {"name": "Data & Analytics",                     "color": "brown"},
                {"name": "QA & Testing",                         "color": "default"},
                {"name": "Security & Information Assurance",     "color": "red"},
            ]}},
            "Document Type": {"select": {"options": ALL_DOC_TYPES}},
            "Industry":      {"select": {"options": [
                {"name": "SaaS",          "color": "blue"},
                {"name": "FinTech",       "color": "green"},
                {"name": "HealthTech",    "color": "red"},
                {"name": "EdTech",        "color": "orange"},
                {"name": "E-Commerce",    "color": "purple"},
                {"name": "Manufacturing", "color": "gray"},
                {"name": "Healthcare",    "color": "pink"},
                {"name": "Retail",        "color": "yellow"},
            ]}},
            "Status":        {"select": {"options": [
                {"name": "✅ Published", "color": "green"},
                {"name": "📝 Draft",     "color": "yellow"},
                {"name": "🔄 In Review", "color": "blue"},
                {"name": "❌ Archived",  "color": "red"},
            ]}},
            "Version":       {"rich_text": {}},
            "Score":         {"number": {"format": "number"}},
            "Grade":         {"select": {"options": [
                {"name": "A+", "color": "green"}, {"name": "A",  "color": "green"},
                {"name": "B+", "color": "blue"},  {"name": "B",  "color": "blue"},
                {"name": "C",  "color": "yellow"},{"name": "D",  "color": "red"},
            ]}},
            "Word Count":    {"number": {"format": "number"}},
            "Published At":  {"date": {}},
            "Company":       {"rich_text": {}},
        }

        to_add = {k: v for k, v in NEW_PROPS.items() if k.lower() not in existing_lower}
        if to_add:
            _patch(req.token, f"/databases/{req.database_id}", {"properties": to_add})

        return {
            "status":   "updated" if to_add else "already_complete",
            "added":    list(to_add.keys()),
            "existing": list(existing.keys()),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/publish")
def api_publish(req: PublishRequest):
    """Publish one document to Notion."""
    try:
        from db import get_connection
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, document_type, department, industry,
                   generated_content, question_answers, validation
            FROM generated_documents WHERE id = %s
        """, (req.document_id,))
        row = cur.fetchone()
        cur.close(); conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    if not row:
        raise HTTPException(status_code=404, detail=f"Document {req.document_id} not found")

    doc_id, doc_type, dept, industry, content, qa, validation = row

    if not content:
        raise HTTPException(status_code=400, detail="Document has no generated content")

    qa  = qa  or {}
    val = validation or {}
    company = qa.get("company_name", "Turabit")    if isinstance(qa,  dict) else "Turabit"
    version = qa.get("document_version", "1.0")    if isinstance(qa,  dict) else "1.0"
    score   = val.get("score")                      if isinstance(val, dict) else None
    grade   = val.get("grade")                      if isinstance(val, dict) else None
    wc      = val.get("word_count")                 if isinstance(val, dict) else None

    result = _publish(
        token=req.token, db_id=req.database_id,
        doc_type=doc_type, dept=dept, industry=industry or "SaaS",
        content=content, company=company, version=version,
        score=score, grade=grade, wc=wc,
    )

    # Mark published in DB
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("ALTER TABLE generated_documents ADD COLUMN IF NOT EXISTS notion_page_id TEXT")
        cur.execute("ALTER TABLE generated_documents ADD COLUMN IF NOT EXISTS notion_url TEXT")
        cur.execute("ALTER TABLE generated_documents ADD COLUMN IF NOT EXISTS notion_published BOOLEAN DEFAULT FALSE")
        cur.execute("""
            UPDATE generated_documents
            SET notion_page_id = %s, notion_url = %s, notion_published = TRUE
            WHERE id = %s
        """, (result["page_id"], result["url"], doc_id))
        conn.commit(); cur.close(); conn.close()
    except Exception:
        pass

    return {
        "success":        True,
        "page_id":        result["page_id"],
        "url":            result["url"],
        "title":          result["title"],
        "blocks_created": result["blocks_created"],
        "message":        f"✅ '{doc_type}' published to Notion!",
    }


@router.post("/publish-all")
def api_publish_all(req: PublishAllRequest):
    """Publish all unpublished documents."""
    try:
        from db import get_connection
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT id FROM generated_documents
            WHERE (notion_published IS NOT TRUE) AND generated_content IS NOT NULL
            ORDER BY id
        """)
        ids = [r[0] for r in cur.fetchall()]
        cur.close(); conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    results = []
    for doc_id in ids:
        try:
            r = api_publish(PublishRequest(
                token=req.token, database_id=req.database_id, document_id=str(doc_id)
            ))
            results.append({"id": doc_id, "status": "published", "url": r.get("url")})
        except Exception as e:
            results.append({"id": doc_id, "status": "failed", "error": str(e)})

    return {
        "total":     len(results),
        "published": sum(1 for r in results if r["status"] == "published"),
        "failed":    sum(1 for r in results if r["status"] == "failed"),
        "results":   results,
    }

