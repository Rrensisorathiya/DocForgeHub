import streamlit as st
import pandas as pd
from datetime import datetime
import time
import json
import re
import requests
import base64
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

# ============================================================
# CONFIG
# ============================================================
API_BASE_URL   = "http://127.0.0.1:8000"
NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# Request timeout constants (seconds)
_SHORT_TIMEOUT  = 10
_MEDIUM_TIMEOUT = 30
_LONG_TIMEOUT   = 300

# ============================================================
# SCHEMA — 13 SaaS Enterprise Departments
# ============================================================
DEPARTMENTS = [
    "HR & People Operations",
    "Legal & Compliance",
    "Sales & Customer Facing",
    "Engineering & Operations",
    "Product & Design",
    "Marketing & Content",
    "Finance & Operations",
    "Partnership & Alliances",
    "IT & Internal Systems",
    "Platform & Infrastructure Operations",
    "Data & Analytics",
    "QA & Testing",
    "Security & Information Assurance",
]

DEPT_DOC_TYPES = {
    "HR & People Operations": [
        "Offer Letter", "Employment Contract", "Employee Handbook",
        "HR Policy Manual", "Onboarding Checklist", "Performance Appraisal Form",
        "Leave Policy Document", "Code of Conduct", "Exit Interview Form",
        "Training & Development Plan",
    ],
    "Legal & Compliance": [
        "Master Service Agreement (MSA)", "Non-Disclosure Agreement (NDA)",
        "Data Processing Agreement (DPA)", "Privacy Policy", "Terms of Service",
        "Compliance Audit Report", "Risk Assessment Report",
        "Intellectual Property Agreement", "Vendor Contract Template",
        "Regulatory Compliance Checklist",
    ],
    "Sales & Customer Facing": [
        "Sales Proposal Template", "Sales Playbook", "Customer Onboarding Guide",
        "Service Level Agreement (SLA)", "Pricing Strategy Document",
        "Customer Case Study", "Sales Contract", "CRM Usage Guidelines",
        "Quarterly Sales Report", "Customer Feedback Report",
    ],
    "Engineering & Operations": [
        "Software Requirements Specification (SRS)", "Technical Design Document (TDD)",
        "API Documentation", "Deployment Guide", "Release Notes",
        "System Architecture Document", "Incident Report",
        "Root Cause Analysis (RCA)", "DevOps Runbook", "Change Management Log",
    ],
    "Product & Design": [
        "Product Requirements Document (PRD)", "Product Roadmap",
        "Feature Specification Document", "UX Research Report",
        "Wireframe Documentation", "Design System Guide", "User Persona Document",
        "A/B Testing Report", "Product Strategy Document", "Competitive Analysis Report",
    ],
    "Marketing & Content": [
        "Marketing Strategy Plan", "Content Calendar", "Brand Guidelines",
        "SEO Strategy Document", "Campaign Performance Report", "Social Media Strategy",
        "Email Marketing Plan", "Press Release Template",
        "Market Research Report", "Lead Generation Plan",
    ],
    "Finance & Operations": [
        "Annual Budget Plan", "Financial Statement Report", "Expense Policy",
        "Invoice Template", "Procurement Policy", "Revenue Forecast Report",
        "Cash Flow Statement", "Vendor Payment Policy",
        "Cost Analysis Report", "Financial Risk Assessment",
    ],
    "Partnership & Alliances": [
        "Partnership Agreement", "Memorandum of Understanding (MoU)",
        "Channel Partner Agreement", "Affiliate Program Agreement",
        "Strategic Alliance Proposal", "Partner Onboarding Guide",
        "Joint Marketing Plan", "Revenue Sharing Agreement",
        "Partner Performance Report", "NDA for Partners",
    ],
    "IT & Internal Systems": [
        "IT Policy Manual", "Access Control Policy", "IT Asset Management Policy",
        "Backup & Recovery Policy", "Network Architecture Document",
        "IT Support SOP", "Disaster Recovery Plan", "Software License Tracking Log",
        "Internal System Audit Report", "Hardware Procurement Policy",
    ],
    "Platform & Infrastructure Operations": [
        "Infrastructure Architecture Document", "Cloud Deployment Guide",
        "Capacity Planning Report", "Infrastructure Monitoring Plan",
        "Incident Response Plan", "SLA for Infrastructure",
        "Configuration Management Document", "Uptime & Availability Report",
        "Infrastructure Security Policy", "Scalability Planning Document",
    ],
    "Data & Analytics": [
        "Data Governance Policy", "Data Dictionary",
        "Business Intelligence (BI) Report", "KPI Dashboard Documentation",
        "Data Pipeline Documentation", "Data Quality Report",
        "Analytics Strategy Document", "Predictive Model Report",
        "Data Privacy Impact Assessment", "Reporting Standards Guide",
    ],
    "QA & Testing": [
        "Test Plan Document", "Test Case Template", "Test Strategy Document",
        "Bug Report Template", "QA Checklist", "Automation Test Plan",
        "Regression Test Report", "UAT Document",
        "Test Coverage Report", "Performance Testing Report",
    ],
    "Security & Information Assurance": [
        "Information Security Policy", "Cybersecurity Risk Assessment",
        "Incident Response Plan", "Vulnerability Assessment Report",
        "Penetration Testing Report", "Access Control Policy",
        "Security Audit Report", "Data Classification Policy",
        "Business Continuity Plan (BCP)", "Security Awareness Training Material",
    ],
}

ALL_DOC_TYPES = sorted({dt for dts in DEPT_DOC_TYPES.values() for dt in dts})

# ← ADD THESE TWO RIGHT HERE
ALL_INDUSTRIES = ["SaaS"]

DEPT_CONTEXT_LABELS = {
    "HR & People Operations":               ("HR Head", "hr_head"),
    "Legal & Compliance":                   ("Legal Entity", "legal_entity"),
    "Sales & Customer Facing":              ("Sales Head", "sales_head"),
    "Engineering & Operations":             ("Engineering Head", "engineering_head"),
    "Product & Design":                     ("Product Owner", "product_owner"),
    "Marketing & Content":                  ("Marketing Head", "marketing_head"),
    "Finance & Operations":                 ("Finance Head", "finance_head"),
    "Partnership & Alliances":              ("Partner Company", "partner_company_name"),
    "IT & Internal Systems":                ("IT Head", "it_head"),
    "Platform & Infrastructure Operations": ("Platform Head", "platform_head"),
    "Data & Analytics":                     ("Data Team Lead", "data_team_lead"),
    "QA & Testing":                         ("QA Team Lead", "qa_team_lead"),
    "Security & Information Assurance":     ("Security Officer", "security_officer"),
}

# ============================================================
# ROBUST API HELPERS  — centralised error handling
# ============================================================

def _is_backend_up() -> bool:
    """Fast liveness probe — returns True/False without side effects."""
    try:
        r = requests.get(f"{API_BASE_URL}/system/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def api_get(endpoint: str, params: dict = None):
    """
    GET from the FastAPI backend.
    Returns parsed JSON on success, None on any failure.
    Shows a user-friendly error only once per session per endpoint type.
    """
    logger.debug(f"API GET request: {endpoint}, params: {params}")
    try:
        r = requests.get(
            f"{API_BASE_URL}{endpoint}",
            params=params,
            timeout=_SHORT_TIMEOUT,
        )
        r.raise_for_status()
        result = r.json()
        logger.debug(f"API GET success: {endpoint}")
        return result
    except requests.exceptions.ConnectionError:
        logger.error(f"API GET Connection Error on {endpoint}")
        _show_backend_offline_once()
        return None
    except requests.exceptions.Timeout:
        logger.warning(f"API GET Timeout on {endpoint}")
        st.warning(f"⏱️ Request timed out: `{endpoint}` — backend may be slow.")
        return None
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        logger.warning(f"API GET HTTP {status} on {endpoint}")
        # 404 is expected for missing templates/questionnaires — suppress noise
        if status != 404:
            st.warning(f"⚠️ API returned HTTP {status} for `{endpoint}`")
        return None
    except Exception as e:
        logger.error(f"API GET Unexpected error on {endpoint}: {str(e)}", exc_info=True)
        st.error(f"❌ Unexpected API error on `{endpoint}`: {str(e)}")
        return None


def api_post(endpoint: str, data: dict, method: str = "POST"):
    """
    POST/PUT to the FastAPI backend.
    Returns parsed JSON on success, None on any failure.
    """
    logger.info(f"API {method} request: {endpoint}")
    logger.debug(f"{method} data: {list(data.keys())}")
    try:
        url = f"{API_BASE_URL}{endpoint}"
        if method == "PUT":
            r = requests.put(url, json=data, timeout=_LONG_TIMEOUT)
        else:
            r = requests.post(url, json=data, timeout=_LONG_TIMEOUT)
        r.raise_for_status()
        result = r.json()
        logger.info(f"API {method} success: {endpoint}")
        return result
    except requests.exceptions.ConnectionError:
        logger.error(f"API {method} Connection Error on {endpoint}")
        st.error(
            "❌ Cannot connect to backend.\n\n"
            "**Fix:** Open a terminal and run:\n```\npython -m uvicorn main:app --reload --port 8000\n```"
        )
        return None
    except requests.exceptions.Timeout:
        logger.error(f"API {method} Timeout on {endpoint} after {_LONG_TIMEOUT}s")
        st.error(
            f"⏱️ {method} to `{endpoint}` timed out after {_LONG_TIMEOUT}s.\n\n"
            "The request may still be running. Check the backend logs."
        )
        return None
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        body   = ""
        try:
            body = e.response.text[:500]
        except Exception:
            pass
        logger.error(f"API {method} HTTP {status} on {endpoint}: {body}")
        st.error(f"❌ HTTP {status} from `{endpoint}`:\n```\n{body}\n```")
        return None
    except Exception as e:
        logger.error(f"API {method} Unexpected error on {endpoint}: {str(e)}", exc_info=True)
        st.error(f"❌ {method} error on `{endpoint}`: {str(e)}")
        return None
def api_delete(endpoint: str):
    """DELETE from the FastAPI backend."""
    logger.info(f"API DELETE request: {endpoint}")
    try:
        r = requests.delete(
            f"{API_BASE_URL}{endpoint}",
            timeout=_SHORT_TIMEOUT,
        )
        r.raise_for_status()
        result = r.json()
        logger.info(f"API DELETE success: {endpoint}")
        return result
    except requests.exceptions.ConnectionError:
        logger.error(f"API DELETE Connection Error on {endpoint}")
        _show_backend_offline_once()
        return None
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        logger.error(f"API DELETE HTTP {status} on {endpoint}")
        st.error(f"❌ Delete failed HTTP {status}: {e.response.text[:200] if e.response else ''}")
        return None
    except Exception as e:
        logger.error(f"API DELETE Unexpected error on {endpoint}: {str(e)}", exc_info=True)
        st.error(f"❌ Delete error: {str(e)}")
        return None


def _show_backend_offline_once():
    """Show backend-offline message — suppressed if already shown this session."""
    key = "_backend_offline_shown"
    if not st.session_state.get(key):
        st.error(
            "❌ **Backend offline.**\n\n"
            "Start the FastAPI server:\n```\npython -m uvicorn main:app --reload --port 8000\n```"
        )
        st.session_state[key] = True


def fetch_file(document_id, fmt: str, retry_count: int = 0, max_retries: int = 2) -> bytes:
    """Download an exported file (docx / pdf) from the backend with retry logic."""
    try:
        # Increased timeout for large document exports
        export_timeout = _LONG_TIMEOUT if fmt in ["pdf", "docx"] else _MEDIUM_TIMEOUT
        
        r = requests.get(
            f"{API_BASE_URL}/export/{document_id}/{fmt}",
            timeout=export_timeout,
        )
        if r.status_code == 200:
            return r.content
        
        # Handle non-200 status codes
        if r.status_code == 504 or r.status_code == 500:
            # Server error - may be worth retrying
            if retry_count < max_retries:
                logger.warning(f"Export attempt {retry_count + 1} failed with {r.status_code}, retrying...")
                st.warning(f"⏳ Export attempt {retry_count + 1}/{max_retries + 1} — Retrying...")
                time.sleep(2 ** retry_count)  # Exponential backoff
                return fetch_file(document_id, fmt, retry_count + 1, max_retries)
        
        st.error(
            f"❌ Export failed ({fmt.upper()}) — HTTP {r.status_code}: {r.text[:200]}"
        )
        return None
        
    except requests.exceptions.Timeout:
        # Timeout error - provide retry option
        if retry_count < max_retries:
            logger.warning(f"Export timeout attempt {retry_count + 1}, retrying...")
            st.warning(f"⏳ Export timeout — Retrying (attempt {retry_count + 1}/{max_retries + 1})...")
            time.sleep(2 ** retry_count)  # Exponential backoff
            return fetch_file(document_id, fmt, retry_count + 1, max_retries)
        else:
            st.error(
                f"❌ Export timeout for {fmt.upper()}: The export took too long. "
                f"The document may be very large. Please try again or regenerate the document."
            )
            return None
            
    except requests.exceptions.ConnectionError:
        _show_backend_offline_once()
        return None
        
    except Exception as e:
        error_msg = str(e)
        if "Read timed out" in error_msg or "timeout" in error_msg.lower():
            if retry_count < max_retries:
                logger.warning(f"Read timeout attempt {retry_count + 1}, retrying...")
                st.warning(f"⏳ Read timeout — Retrying (attempt {retry_count + 1}/{max_retries + 1})...")
                time.sleep(2 ** retry_count)
                return fetch_file(document_id, fmt, retry_count + 1, max_retries)
        
        st.error(f"❌ Export error: {error_msg}")
        return None


def to_markdown(doc: dict) -> str:
    header = (
        f"---\n"
        f"Type       : {doc.get('document_type','')}\n"
        f"Department : {doc.get('department','')}\n"
        f"Industry   : {doc.get('industry','')}\n"
        f"Date       : {doc.get('created_at','')[:16]}\n"
        f"---\n\n"
    )
    return header + doc.get("generated_content", "")


def safe_fname(doc_type: str, department: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '_', f"{doc_type}_{department}")


# ============================================================
# NOTION HELPERS
# ============================================================
def notion_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _clean_db_id(raw: str) -> str:
    return raw.strip().replace("-", "").replace(" ", "")


def notion_test(token: str) -> tuple:
    try:
        r = requests.get(
            f"{NOTION_API_URL}/users/me",
            headers=notion_headers(token),
            timeout=_SHORT_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            name = (
                data.get("name")
                or data.get("bot", {}).get("owner", {}).get("user", {}).get("name", "Integration")
            )
            return True, f"Connected as: **{name}**"
        elif r.status_code == 401:
            return False, "Invalid token. Re-copy from notion.so/my-integrations."
        else:
            return False, f"Unexpected response ({r.status_code}): {r.text[:200]}"
    except Exception as e:
        return False, f"Connection error: {str(e)}"


def notion_test_database(token: str, database_id: str) -> tuple:
    clean_id = _clean_db_id(database_id)
    try:
        r = requests.get(
            f"{NOTION_API_URL}/databases/{clean_id}",
            headers=notion_headers(token),
            timeout=_SHORT_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            title_arr = data.get("title", [])
            db_name = title_arr[0]["plain_text"] if title_arr else "Untitled"
            props = list(data.get("properties", {}).keys())
            return True, f"Database **{db_name}** found. Columns: {', '.join(props)}"
        elif r.status_code == 404:
            return False, "Database not found. Share the database with your integration (DB → ... → Connections)."
        elif r.status_code == 401:
            return False, "Token is invalid or expired."
        else:
            return False, f"Error {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return False, f"Connection error: {str(e)}"


def notion_databases(token: str) -> list:
    try:
        r = requests.post(
            f"{NOTION_API_URL}/search",
            headers=notion_headers(token),
            json={
                "filter": {"value": "database", "property": "object"},
                "sort": {"direction": "descending", "timestamp": "last_edited_time"},
                "page_size": 50,
            },
            timeout=_SHORT_TIMEOUT,
        )
        if r.status_code == 200:
            return [
                {
                    "id": db["id"],
                    "name": (db.get("title") or [{}])[0].get("plain_text", "Untitled"),
                }
                for db in r.json().get("results", [])
            ]
        return []
    except Exception:
        return []


# ============================================================
# NOTION BLOCK BUILDERS
# ============================================================

def _rich_text(text: str) -> list:
    if not text:
        return [{"type": "text", "text": {"content": ""}}]
    segments = []
    pattern = re.compile(
        r'(\*\*\*(.+?)\*\*\*)'
        r'|(\*\*(.+?)\*\*)'
        r'|(\*(.+?)\*)'
        r'|(`(.+?)`)'
        r'|([^*`]+)',
        re.DOTALL,
    )
    for m in pattern.finditer(text):
        if m.group(1):
            raw, ann = m.group(2), {"bold": True, "italic": True}
        elif m.group(3):
            raw, ann = m.group(4), {"bold": True, "italic": False}
        elif m.group(5):
            raw, ann = m.group(6), {"bold": False, "italic": True}
        elif m.group(7):
            raw, ann = m.group(8), {"code": True, "bold": False, "italic": False}
        else:
            raw, ann = m.group(0), {"bold": False, "italic": False}
        if not raw:
            continue
        for i in range(0, len(raw), 2000):
            segments.append(
                {"type": "text", "text": {"content": raw[i : i + 2000]}, "annotations": ann}
            )
    return segments or [{"type": "text", "text": {"content": text[:2000]}}]


def _is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def _is_separator_row(line: str) -> bool:
    return bool(re.match(r'^\|[\s\-:|]+\|$', line.strip()))


def _parse_table_row(line: str) -> list:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _build_notion_table(rows: list) -> dict:
    if not rows:
        return None
    col_count = max(len(r) for r in rows)
    padded = [row + [""] * (col_count - len(row)) for row in rows]
    children = []
    for row in padded:
        cells = [
            (
                _rich_text(cell)
                if cell
                else [{"type": "text", "text": {"content": ""}}]
            )
            for cell in row
        ]
        children.append({"type": "table_row", "table_row": {"cells": cells}})
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": col_count,
            "has_column_header": True,
            "has_row_header": False,
            "children": children,
        },
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _table_of_contents() -> dict:
    return {"object": "block", "type": "table_of_contents", "table_of_contents": {"color": "default"}}


def _callout(text: str, emoji: str = "📋", color: str = "blue_background") -> dict:
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": _rich_text(text[:2000]),
            "icon": {"type": "emoji", "emoji": emoji},
            "color": color,
        },
    }


def _heading(text: str, level: int = 2) -> dict:
    ht = f"heading_{level}"
    clean = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text).strip()
    return {
        "object": "block",
        "type": ht,
        ht: {"rich_text": [{"type": "text", "text": {"content": clean[:100]}}]},
    }


def _paragraph(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": _rich_text(text)},
    }


def _bullet(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": _rich_text(text)},
    }


def _numbered(text: str) -> dict:
    return {
        "object": "block",
        "type": "numbered_list_item",
        "numbered_list_item": {"rich_text": _rich_text(text)},
    }


def _quote(text: str) -> dict:
    return {"object": "block", "type": "quote", "quote": {"rich_text": _rich_text(text)}}


def _toggle(label: str, children: list) -> dict:
    return {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": [{"type": "text", "text": {"content": label[:200]}}],
            "children": children[:100],
        },
    }


# ============================================================
# MARKDOWN → NOTION BLOCKS
# ============================================================

def parse_inline_markdown(text):
    """Parse **bold** and *italic* inline markdown into Notion rich_text."""
    import re
    parts = []
    pattern = r'(\*\*(.+?)\*\*|\*(.+?)\*|([^*]+))'
    for m in re.finditer(pattern, text):
        if m.group(2):
            parts.append({"type": "text", "text": {"content": m.group(2)},
                          "annotations": {"bold": True, "italic": False}})
        elif m.group(3):
            parts.append({"type": "text", "text": {"content": m.group(3)},
                          "annotations": {"bold": False, "italic": True}})
        elif m.group(4):
            parts.append({"type": "text", "text": {"content": m.group(4)}})
    return parts if parts else [{"type": "text", "text": {"content": text}}]

def markdown_to_notion_blocks(content):
    """Convert markdown content to Notion block objects including tables."""
    blocks = []
    lines = content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        # ── TABLE DETECTION ──────────────────────────────────────────
        if line.strip().startswith("|") and line.strip().endswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            # Remove separator row (|---|---|)
            table_rows = [
                row for row in table_lines
                if not all(c in "-| :" for c in row)
            ]

            if not table_rows:
                continue

            # Parse each row into cells
            def parse_row(row):
                cells = [c.strip() for c in row.strip("|").split("|")]
                return cells

            parsed_rows = [parse_row(r) for r in table_rows]
            num_cols = max(len(r) for r in parsed_rows)

            # Build Notion table block
            table_block = {
                "object": "block",
                "type": "table",
                "table": {
                    "table_width": num_cols,
                    "has_column_header": True,
                    "has_row_header": False,
                    "children": []
                }
            }

            for row_idx, row in enumerate(parsed_rows):
                # Pad row if fewer cells than max
                while len(row) < num_cols:
                    row.append("")

                cells = []
                for cell in row:
                    cells.append([{
                        "type": "text",
                        "text": {"content": cell},
                        "annotations": {
                            "bold": row_idx == 0  # First row = header (bold)
                        }
                    }])

                table_block["table"]["children"].append({
                    "type": "table_row",
                    "table_row": {"cells": cells}
                })

            blocks.append(table_block)
            continue  # i already advanced inside while loop

        # ── DIVIDER ──────────────────────────────────────────────────
        if line.strip() == "---":
            blocks.append({"object": "block", "type": "divider", "divider": {}})

        # ── HEADINGS ─────────────────────────────────────────────────
        elif line.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:].strip()}}]}})

        elif line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:].strip()}}]}})

        elif line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:].strip()}}]}})

        # ── BULLET LIST ──────────────────────────────────────────────
        elif line.startswith("- ") or line.startswith("* "):
            rich = parse_inline_markdown(line[2:].strip())
            blocks.append({"object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": rich}})

        # ── NUMBERED LIST ────────────────────────────────────────────
        elif len(line) > 2 and line[0].isdigit() and (line[1:3] in (". ", ") ")):
            rich = parse_inline_markdown(line[3:].strip())
            blocks.append({"object": "block", "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": rich}})

        # ── PARAGRAPH ────────────────────────────────────────────────
        elif line.strip():
            rich = parse_inline_markdown(line.strip()[:2000])
            blocks.append({"object": "block", "type": "paragraph",
                "paragraph": {
    "rich_text": [{"type": "text", "text": {"content": line.strip()[:2000]}}]
}})

        i += 1

    return blocks
# ============================================================
# SECTION SPLITTER
# ============================================================

def _split_into_sections(blocks: list, max_per_section: int = 80) -> list:
    if not blocks:
        return [{"label": "Content", "blocks": [_paragraph("(empty)")]}]

    sections = []
    cur_label = "Introduction"
    cur_blocks = []

    def flush(label, blist):
        if not blist:
            return
        for part_num, start in enumerate(range(0, len(blist), max_per_section), 1):
            chunk = blist[start : start + max_per_section]
            suffix = f" (Part {part_num})" if len(blist) > max_per_section else ""
            sections.append({"label": label + suffix, "blocks": chunk})

    for block in blocks:
        btype = block.get("type", "")
        if btype in ("heading_1", "heading_2", "heading_3"):
            flush(cur_label, cur_blocks)
            rt = block.get(btype, {}).get("rich_text", [])
            cur_label = rt[0]["text"]["content"] if rt else "Section"
            cur_blocks = []
        else:
            cur_blocks.append(block)

    flush(cur_label, cur_blocks)
    return sections


# ============================================================
# LOW-LEVEL: append blocks to Notion with retry
# ============================================================

def _append_blocks_to_page(token: str, block_id: str, blocks: list) -> list:
    headers = notion_headers(token)
    errors = []
    BATCH = 95

    for start in range(0, len(blocks), BATCH):
        batch = blocks[start : start + BATCH]
        for attempt in range(4):
            try:
                resp = requests.patch(
                    f"{NOTION_API_URL}/blocks/{block_id}/children",
                    headers=headers,
                    json={"children": batch},
                    timeout=60,
                )
                if resp.status_code == 200:
                    break
                elif resp.status_code == 429:
                    time.sleep(2 ** (attempt + 1))
                else:
                    errors.append(
                        f"Batch {start // BATCH + 1}: HTTP {resp.status_code} — {resp.text[:150]}"
                    )
                    break
            except Exception as e:
                if attempt == 3:
                    errors.append(f"Batch {start // BATCH + 1}: {str(e)}")
                else:
                    time.sleep(1)
        if start + BATCH < len(blocks):
            time.sleep(0.5)

    return errors


# # ============================================================
# # NOTION PUBLISH
# # ============================================================

import requests

NOTION_API_URL = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"
_SHORT_TIMEOUT = 20


def notion_headers(token):
    """Return standard Notion API headers."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": _NOTION_VERSION,
    }


def detect_notion_title_column(database_id, token):
    """Detect the title column name in a Notion database."""

    resp = requests.get(
        f"{NOTION_API_URL}/databases/{database_id}",
        headers=notion_headers(token),
        timeout=_SHORT_TIMEOUT,
    )

    if resp.status_code != 200:
        raise Exception(f"Failed to fetch Notion schema: {resp.text}")

    props = resp.json().get("properties", {})

    for col, meta in props.items():
        if meta.get("type") == "title":
            return col, props

    raise Exception("No title column found in Notion database.")


def build_notion_properties(doc, doc_type, db_props, title_col):
    """Create the properties payload for Notion — exact column names."""
    import datetime
    department  = doc.get("department", "")
    industry    = doc.get("industry", "")
    qa          = doc.get("question_answers", {}) or {}
    company     = qa.get("company_name", "") if isinstance(qa, dict) else ""
    metadata    = doc.get("metadata", {}) or {}
    word_count  = int(metadata.get("word_count", 0) or 0)
    doc_type_val = doc.get("document_type", doc_type)
    page_title  = f"{doc_type_val} — {company or department}"

    properties = {
        title_col: {"title": [{"text": {"content": page_title[:100]}}]}
    }

    # Department — select
    if "Department" in db_props:
        properties["Department"] = {"select": {"name": department}}

    # Document Type — select
    if "Document Type" in db_props:
        properties["Document Type"] = {"select": {"name": doc_type_val}}

    # Industry — select
    if "Industry" in db_props:
        properties["Industry"] = {"select": {"name": industry}}

    # Status — select
    if "Status" in db_props:
        properties["Status"] = {"select": {"name": "Published"}}

    # Company — rich_text
    if "Company" in db_props:
        properties["Company"] = {"rich_text": [{"text": {"content": company or ""}}]}

    # Version — rich_text
    if "Version" in db_props:
        properties["Version"] = {"rich_text": [{"text": {"content": "v1"}}]}

    # Word Count — number
    if "Word Count" in db_props:
        properties["Word Count"] = {"number": word_count}

    # Score — number
    if "Score" in db_props:
        properties["Score"] = {"number": 0}

    # Grade — select
    if "Grade" in db_props:
        properties["Grade"] = {"select": {"name": "N/A"}}

    # Published At — date
    if "Published At" in db_props:
        properties["Published At"] = {"date": {"start": datetime.datetime.now().strftime("%Y-%m-%d")}}

    return properties

def create_notion_page(database_id, token, properties):
    """Create a page inside the Notion database."""

    payload = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }

    resp = requests.post(
        f"{NOTION_API_URL}/pages",
        headers=notion_headers(token),
        json=payload,
        timeout=_SHORT_TIMEOUT,
    )

    if resp.status_code != 200:
        raise Exception(f"Failed to create page: {resp.text}")

    return resp.json()["id"]


def publish_document_to_notion(doc, doc_type, content, clean_id, token):
    """Publish document metadata to Notion."""

    if not content or not content.strip():
        return False, "Document content is empty — nothing to publish.", ""

    try:
        # Detect schema
        title_col, db_props = detect_notion_title_column(clean_id, token)

        # Build properties
        properties = build_notion_properties(doc, doc_type, db_props, title_col)

        # Create page
        page_id = create_notion_page(clean_id, token, properties)
        
        # ADD DOCUMENT CONTENT TO NOTION PAGE
        add_content_to_notion(page_id, token, content)

        return True, "Document published successfully.", page_id

    except Exception as e:
        return False, f"Notion publish failed: {str(e)}", ""
    
import time
import requests

def add_content_to_notion(page_id, token, content):
    """Add full document to Notion - handles large docs with rate limiting."""
    
    if not content or not content.strip():
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    all_blocks = markdown_to_notion_blocks(content)
    total = len(all_blocks)
    print(f"📄 Total blocks: {total}")

    chunk_size = 50  # ← reduced from 100 to 50
    total_chunks = (total + chunk_size - 1) // chunk_size

    for i in range(0, total, chunk_size):
        chunk = all_blocks[i:i + chunk_size]
        chunk_num = i // chunk_size + 1

        # Retry up to 3 times per chunk
        for attempt in range(3):
            try:
                resp = requests.patch(
                    f"https://api.notion.com/v1/blocks/{page_id}/children",
                    headers=headers,
                    json={"children": chunk},
                    timeout=60,
                )

                if resp.status_code == 200:
                    print(f"✅ Chunk {chunk_num}/{total_chunks} uploaded")
                    break  # success

                elif resp.status_code == 429:
                    # Rate limited — wait and retry
                    wait = int(resp.headers.get("Retry-After", 2))
                    print(f"⏳ Rate limited, waiting {wait}s...")
                    time.sleep(wait)

                else:
                    print(f"❌ Chunk {chunk_num} failed: {resp.status_code} {resp.text[:200]}")
                    if attempt == 2:
                        raise Exception(f"Chunk {chunk_num} failed after 3 attempts: {resp.text}")
                    time.sleep(1)

            except requests.exceptions.Timeout:
                print(f"⏱️ Timeout on chunk {chunk_num}, attempt {attempt+1}")
                time.sleep(2)

        # Small delay between chunks to avoid rate limit
        time.sleep(0.4)

    print(f"✅ All {total} blocks uploaded to Notion successfully!")
            
def notion_publish(doc, doc_type, content, database_id, token, pdf_bytes=None):
    try:
        clean_id = database_id.replace("-", "").strip()

        # Check if same document type already published → UPDATE instead of CREATE
        existing_page_id = None
        existing_version = 1
        try:
            from db import get_connection as _get_conn
            _conn = _get_conn()
            _cur = _conn.cursor()
            _cur.execute("""
                SELECT notion_page_id, notion_version
                FROM generated_documents
                WHERE document_type = %s
                AND notion_page_id IS NOT NULL
                AND notion_published = TRUE
                AND id != %s
                ORDER BY id DESC LIMIT 1
            """, (doc_type, str(doc.get("id", 0))))
            row = _cur.fetchone()
            if row:
                existing_page_id = row[0]
                existing_version = row[1] or 1
            _cur.close()
            _conn.close()
        except Exception:
            pass

        # If same type exists → UPDATE that Notion page
        if existing_page_id:
            new_version = existing_version + 1
            ok, notion_url, page_id = notion_update_page(
                page_id=existing_page_id,
                token=token,
                content=content,
                version=new_version,
            )
            if ok:
                # Clear old document notion data
                try:
                    from db import get_connection as _get_conn2
                    _conn2 = _get_conn2()
                    _cur2 = _conn2.cursor()
                    _cur2.execute("""
                        UPDATE generated_documents
                        SET notion_page_id = NULL,
                            notion_published = FALSE,
                            notion_url = NULL
                        WHERE document_type = %s
                        AND notion_page_id = %s
                    """, (doc_type, existing_page_id))
                    _conn2.commit()
                    _cur2.close()
                    _conn2.close()
                except Exception:
                    pass
                return True, notion_url, page_id

        # No existing page → CREATE new Notion page
        ok, msg, page_id = publish_document_to_notion(
            doc, doc_type, content, clean_id, token
        )
        if not ok:
            return False, msg, ""
        notion_url = f"https://www.notion.so/{page_id.replace('-', '')}"
        return True, notion_url, page_id

    except Exception as e:
        return False, str(e), ""

def notion_update_page(page_id: str, token: str, content: str, version: int) -> tuple:
    """Update existing Notion page — delete ALL blocks with pagination, then add new content."""
    try:
        import datetime, time
        headers = notion_headers(token)

        # Step 1: Delete ALL existing blocks (paginated)
        has_more = True
        cursor = None
        deleted_count = 0
        while has_more:
            params = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor

            resp = requests.get(
                f"{NOTION_API_URL}/blocks/{page_id}/children",
                headers=headers,
                params=params,
                timeout=30,
            )
            if resp.status_code != 200:
                break

            data = resp.json()
            blocks = data.get("results", [])
            has_more = data.get("has_more", False)
            cursor = data.get("next_cursor")

            for block in blocks:
                del_resp = requests.delete(
                    f"{NOTION_API_URL}/blocks/{block['id']}",
                    headers=headers,
                    timeout=10,
                )
                if del_resp.status_code == 200:
                    deleted_count += 1
                time.sleep(0.05)  # Rate limit protection

        # Step 2: Update page properties — version + word count
        word_count = len(content.split())
        prop_update = {
            "properties": {
                "Version":      {"rich_text": [{"text": {"content": f"v{version}"}}]},
                "Word Count":   {"number": word_count},
                "Status":       {"select": {"name": "Published"}},
                "Published At": {"date": {"start": datetime.datetime.now().strftime("%Y-%m-%d")}},
            }
        }
        requests.patch(
            f"{NOTION_API_URL}/pages/{page_id}",
            headers=headers,
            json=prop_update,
            timeout=30,
        )

        # Step 3: Add new content
        add_content_to_notion(page_id, token, content)

        notion_url = f"https://www.notion.so/{page_id.replace('-', '')}"
        return True, notion_url, page_id

    except Exception as e:
        return False, str(e), ""

def load_css():
    st.markdown(
        """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg,#1e3c72 0%,#2a5298 100%); }
    .main-header { font-size:2.2rem; font-weight:700; color:#1e3c72; text-align:center; margin-bottom:8px; }
    .sub-header  { font-size:1.5rem; font-weight:600; color:#2a5298; border-bottom:3px solid #4CAF50; padding-bottom:8px; margin:25px 0 15px; }
    .stat-box    { background:linear-gradient(135deg,#667eea,#764ba2); color:white; padding:28px 20px 24px 20px; border-radius:14px; text-align:center; margin:4px 6px 12px 6px; }
    .metric-box { background:linear-gradient(135deg,#667eea,#764ba2); color:white; padding:20px 16px; border-radius:14px; text-align:center; margin:2px 4px 8px 4px; min-height:110px; height:110px; display:flex; flex-direction:column; align-items:center; justify-content:center; box-shadow:0 4px 15px rgba(102,126,234,0.35); transition:transform 0.2s; }
    .metric-box:hover { transform:translateY(-3px); box-shadow:0 8px 25px rgba(102,126,234,0.5); }
    .metric-box.perfect { background:linear-gradient(135deg,#f7971e,#ffd200); box-shadow:0 4px 20px rgba(255,200,0,0.5); }
    .metric-number { font-size:2rem; font-weight:700; margin-bottom:6px; line-height:1.2; }
    .metric-label { font-size:0.70rem; opacity:.85; text-transform:uppercase; letter-spacing:2px; margin-top:2px; }
    .metric-checks { display:flex; gap:16px; align-items:center; justify-content:center; margin-bottom:6px; }
    .metric-check-num { font-size:2rem; font-weight:700; }
    .metric-check-icon { font-size:0.70rem; opacity:0.85; text-transform:uppercase; letter-spacing:1.5px; }
    .stat-number { font-size:2rem; font-weight:700; margin-bottom:8px; }
    .stat-label  { font-size:0.8rem; opacity:.9; text-transform:uppercase; letter-spacing:1px; margin-top:4px; }
    .doc-card    { background:white; padding:18px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.08); margin-bottom:12px; border:2px solid #e0e0e0; }
    .doc-card:hover { border-color:#4CAF50; }
    .custom-card { background:white; padding:22px; border-radius:14px; box-shadow:0 3px 8px rgba(0,0,0,.1); margin-bottom:18px; border-left:5px solid #4CAF50; }
    .success-box { background:linear-gradient(135deg,#11998e,#38ef7d); color:white; padding:18px; border-radius:12px; margin:15px 0; text-align:center; font-weight:600; }
    .info-box    { background:linear-gradient(135deg,#4facfe,#00f2fe); color:white; padding:18px; border-radius:12px; margin:15px 0; }
    .warn-box    { background:linear-gradient(135deg,#f7971e,#ffd200); color:#333; padding:14px; border-radius:10px; margin:12px 0; }
    .q-block     { background:#f8f9ff; border-left:4px solid #667eea; padding:12px 18px; border-radius:8px; margin-bottom:12px; }
    .badge-type  { background:linear-gradient(135deg,#f093fb,#f5576c); color:white; padding:4px 14px; border-radius:20px; font-size:.8rem; font-weight:600; display:inline-block; }
    .badge-done  { background:#4CAF50; color:white; padding:4px 12px; border-radius:14px; font-size:.8rem; font-weight:600; }
    .badge-draft { background:#FF9800; color:white; padding:4px 12px; border-radius:14px; font-size:.8rem; font-weight:600; }
    .divider     { height:3px; background:linear-gradient(90deg,#667eea,#764ba2); border:none; margin:25px 0; border-radius:5px; }
    .stButton>button { background:linear-gradient(135deg,#667eea,#764ba2); color:white; border:none; border-radius:8px; padding:10px 28px; font-weight:600; box-shadow:0 3px 8px rgba(0,0,0,.2); }
    .dl-box { background:#f0f4ff; border:2px solid #667eea; border-radius:12px; padding:20px; margin:15px 0; }
    .stDownloadButton>button {background:linear-gradient(135deg,#667eea,#764ba2);color:white;border:none; border-radius:8px;padding:10px 28px;font-weight:600;box-shadow:0 3px 8px rgba(0,0,0,.2);}
    .stLinkButton>a {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    font-weight: 600 !important;
    text-decoration: none !important;
    display: block !important;
    text-align: center !important;
    box-shadow: 0 3px 8px rgba(0,0,0,.2) !important;
}
    .dept-chip { display:inline-block; background:#e8f4fd; color:#1e3c72; padding:3px 10px; border-radius:20px; font-size:.78rem; font-weight:600; margin:2px; }
    </style>
    """,
        unsafe_allow_html=True,
    )


# ============================================================
# SESSION STATE
# ============================================================
def init_session():
    logger.debug("Initializing session state")
    defaults = {
        "page": "Home",
        "gen_step": 1,
        "sel_industry": "SaaS",
        "sel_dept": None,
        "sel_type": None,
        "qa": {},
        "last_doc": None,
        "notion_published": {},
        "_backend_offline_shown": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    logger.debug("Session state initialized")


# ============================================================
# CACHED API CALLS  (fallback to local schema if API offline)
# ============================================================

@st.cache_data(ttl=300)
def get_departments():
    logger.debug("Fetching departments list")
    data = api_get("/templates/departments")
    if data and data.get("departments"):
        logger.debug(f"Fetched {len(data['departments'])} departments from API")
        return data["departments"]
    logger.debug("Using fallback departments list")
    return DEPARTMENTS


@st.cache_data(ttl=300)
def get_doc_types_for_dept(dept: str) -> list:
    logger.debug(f"Fetching document types for department: {dept}")
    data = api_get("/questionnaires/document-types", params={"department": dept})
    if data and data.get("document_types"):
        logger.debug(f"Fetched {len(data['document_types'])} types for {dept}")
        return data["document_types"]
    return DEPT_DOC_TYPES.get(dept, [])


@st.cache_data(ttl=300)
def get_all_doc_types() -> list:
    logger.debug("Fetching all document types")
    data = api_get("/templates/document-types")
    if data and data.get("document_types"):
        logger.debug(f"Fetched {len(data['document_types'])} total document types")
        return data["document_types"]
    return ALL_DOC_TYPES


@st.cache_data(ttl=300)
def get_questions(dept: str, doc_type: str) -> list:
    """
    Fetch questions — tries three endpoints with graceful fallback.
    1. /questionnaires/full  (preferred — returns all categories merged)
    2. /questionnaires/by-type  (legacy)
    3. Local schema fallback (offline mode)
    """
    logger.debug(f"Fetching questions for {dept} - {doc_type}")
    
    # Try preferred endpoint
    data = api_get("/questionnaires/full", params={"department": dept, "document_type": doc_type})
    if data and data.get("questions"):
        qs = data["questions"]
        for q in qs:
            if "category" not in q:
                q["category"] = "common"
        logger.debug(f"Fetched {len(qs)} questions from /questionnaires/full")
        return qs

    # Try legacy endpoint
    logger.debug("Falling back to /questionnaires/by-type")
    data = api_get("/questionnaires/by-type", params={"department": dept, "document_type": doc_type})
    if data and "questions" in data:
        logger.debug(f"Fetched {len(data['questions'])} questions from legacy endpoint")
        return data["questions"]

    # Offline fallback
    logger.debug("Using offline fallback questions")
    return _build_fallback_questions(dept, doc_type)


def _build_fallback_questions(dept: str, doc_type: str) -> list:
    """Minimal question set built from local schema when API is offline."""
    dept_ctx_label, dept_ctx_id = DEPT_CONTEXT_LABELS.get(dept, ("Department Head", "dept_head"))
    return [
        # Common
        {"id": "company_name",     "question": "Company name?",                        "type": "text",   "required": True,  "options": [], "category": "common"},
        {"id": dept_ctx_id,        "question": f"{dept_ctx_label} name?",               "type": "text",   "required": False, "options": [], "category": "common"},
        {"id": "company_location", "question": "Company headquarters location?",        "type": "text",   "required": False, "options": [], "category": "common"},
        {"id": "company_size",     "question": "Company size?",                         "type": "select", "required": False,
         "options": ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"],       "category": "common"},
        {"id": "work_model",       "question": "Work model?",                           "type": "select", "required": False,
         "options": ["Remote", "Hybrid", "On-site"],                                   "category": "common"},
        {"id": "primary_product",  "question": "Primary product or service?",           "type": "text",   "required": False, "options": [], "category": "common"},
        {"id": "target_market",    "question": "Target market (B2B / B2C / Both)?",     "type": "select", "required": False,
         "options": ["B2B", "B2C", "B2B & B2C"],                                       "category": "common"},
        # Metadata
        {"id": "document_title",   "question": "Document title (or leave blank for default)?", "type": "text",   "required": False, "options": [], "category": "metadata"},
        {"id": "author_name",      "question": "Document author name?",                 "type": "text",   "required": False, "options": [], "category": "metadata"},
        {"id": "approved_by",      "question": "Approved by (name or role)?",           "type": "text",   "required": False, "options": [], "category": "metadata"},
        {"id": "document_version", "question": "Document version (e.g. 1.0)?",          "type": "text",   "required": False, "options": [], "category": "metadata"},
        {"id": "effective_date",   "question": "Effective date of this document?",      "type": "date",   "required": False, "options": [], "category": "metadata"},
        # Document-type specific
        {"id": "specific_focus",   "question": f"Specific focus for this {doc_type}?",  "type": "textarea","required": False, "options": [], "category": "document_type_specific"},
        {"id": "tools_used",       "question": "Key tools used by this department?",    "type": "text",   "required": False, "options": [], "category": "document_type_specific"},
        {"id": "tone_preference",  "question": "Preferred tone?",                       "type": "select", "required": False,
         "options": ["Professional & Formal", "Professional & Friendly", "Technical & Detailed", "Executive-level & Concise"],
         "category": "document_type_specific"},
        {"id": "geographic_locations", "question": "Geographic locations / jurisdictions covered?", "type": "text", "required": False, "options": [], "category": "document_type_specific"},
        {"id": "compliance_req",   "question": "Compliance or regulatory requirements?", "type": "text",  "required": False, "options": [], "category": "document_type_specific"},
        {"id": "additional_ctx",   "question": "Any additional context or instructions?","type": "textarea","required": False, "options": [], "category": "document_type_specific"},
    ]


@st.cache_data(ttl=60)
def get_stats():
    logger.debug("Fetching system statistics")
    stats = api_get("/system/stats")
    if stats:
        logger.debug(f"Stats retrieved: {stats}")
    return stats


@st.cache_data(ttl=30)
def get_docs(dept=None, dtype=None):
    logger.debug(f"Fetching documents - dept={dept}, type={dtype}")
    params = {}
    if dept:
        params["department"] = dept
    if dtype:
        params["document_type"] = dtype
    result = api_get("/documents/", params=params)
    # Handle both list and dict responses
    if isinstance(result, list):
        logger.debug(f"Retrieved {len(result)} documents (list format)")
        return result
    if isinstance(result, dict):
        docs = result.get("documents", result.get("items", []))
        logger.debug(f"Retrieved {len(docs)} documents (dict format)")
        return docs
    logger.debug("No documents retrieved")
    return []


# ============================================================
# DOWNLOAD WIDGET
# ============================================================

def render_download_buttons(
    document_id, doc_type: str, department: str, full_doc: dict = None, key_prefix: str = "dl"
):
    fname = safe_fname(doc_type, department)
    st.markdown("**⬇️ Download this document:**")
    with st.container():
        c1, c2, c3 = st.columns([1, 1, 1], gap="medium")
    
    with c1:
        if st.button(
            "📘 Prepare Word (.docx)", key=f"{key_prefix}_prep_docx_{document_id}", use_container_width=True
        ):
            st.session_state[f"{key_prefix}_fetch_docx_{document_id}"] = True
            st.session_state[f"{key_prefix}_error_docx_{document_id}"] = False
            
        if st.session_state.get(f"{key_prefix}_fetch_docx_{document_id}"):
            with st.spinner("Generating Word file..."):
                data = fetch_file(document_id, "docx")
            if data:
                st.session_state[f"{key_prefix}_error_docx_{document_id}"] = False
                st.download_button(
                    "⬇️ Click to Download .docx",
                    data=data,
                    file_name=f"{fname}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"{key_prefix}_docx_{document_id}",
                    use_container_width=True,
                )
            else:
                st.session_state[f"{key_prefix}_error_docx_{document_id}"] = True
                
        # Show regenerate button if export failed
        if st.session_state.get(f"{key_prefix}_error_docx_{document_id}"):
            if st.button(
                "🔄 Regenerate .docx", 
                key=f"{key_prefix}_regen_docx_{document_id}", 
                use_container_width=True
            ):
                st.session_state[f"{key_prefix}_fetch_docx_{document_id}"] = True
                st.session_state[f"{key_prefix}_error_docx_{document_id}"] = False
                st.rerun()
    
    with c2:
        if st.button(
            "📕 Prepare PDF (.pdf)", key=f"{key_prefix}_prep_pdf_{document_id}", use_container_width=True
        ):
            st.session_state[f"{key_prefix}_fetch_pdf_{document_id}"] = True
            st.session_state[f"{key_prefix}_error_pdf_{document_id}"] = False
            
        if st.session_state.get(f"{key_prefix}_fetch_pdf_{document_id}"):
            with st.spinner("Generating PDF file..."):
                data = fetch_file(document_id, "pdf")
            if data:
                st.session_state[f"{key_prefix}_error_pdf_{document_id}"] = False
                st.download_button(
                    "⬇️ Click to Download .pdf",
                    data=data,
                    file_name=f"{fname}.pdf",
                    mime="application/pdf",
                    key=f"{key_prefix}_pdf_{document_id}",
                    use_container_width=True,
                )
            else:
                st.session_state[f"{key_prefix}_error_pdf_{document_id}"] = True
        
        # Show regenerate button if export failed
        if st.session_state.get(f"{key_prefix}_error_pdf_{document_id}"):
            if st.button(
                "🔄 Regenerate .pdf", 
                key=f"{key_prefix}_regen_pdf_{document_id}", 
                use_container_width=True
            ):
                st.session_state[f"{key_prefix}_fetch_pdf_{document_id}"] = True
                st.session_state[f"{key_prefix}_error_pdf_{document_id}"] = False
                st.rerun()
    
    with c3:
        if full_doc is None:
            full_doc = api_get(f"/documents/{document_id}")
        if full_doc:
            st.download_button(
                "📄 Download Markdown (.md)",
                data=to_markdown(full_doc),
                file_name=f"{fname}.md",
                mime="text/markdown",
                key=f"{key_prefix}_md_{document_id}",
                use_container_width=True,
            )


# ============================================================
# SIDEBAR
# ============================================================

def render_sidebar():
    logger.debug("Rendering sidebar")
    with st.sidebar:
        st.markdown(
            "<h1 style='color:white;text-align:center;margin-bottom:15px;'>📄 DocForgeHub</h1>",
            unsafe_allow_html=True,
        )

        # Backend health indicator
        is_up = _is_backend_up()
        logger.debug(f"Backend health check: {'UP' if is_up else 'DOWN'}")
        color = "#4CAF50" if is_up else "#f44336"
        label = "🟢 Backend Connected" if is_up else "🔴 Backend Offline"
        st.markdown(
            f"<div style='background:{color};padding:7px;border-radius:8px;"
            f"text-align:center;color:white;font-size:.85rem;margin-bottom:12px;'>{label}</div>",
            unsafe_allow_html=True,
        )

        if not is_up:
            st.markdown(
                "<div style='color:#ffd700;font-size:.78rem;text-align:center;padding:6px;'>"
                "Run: <code>uvicorn main:app --reload</code></div>",
                unsafe_allow_html=True,
            )

        # Reset offline warning on reconnect
        if is_up:
            st.session_state["_backend_offline_shown"] = False

        st.markdown("<hr style='border:1px solid rgba(255,255,255,.3);'>", unsafe_allow_html=True)

        pages = {
            "🏠 Home": "Home",
            "✨ Generate": "Generate",
            "📚 Library": "Library",
            "🗂 Templates": "Templates",
            "❓ Questionnaires": "Questionnaires",
            "🚀 Publish to Notion": "Notion",
            "📊 Stats": "Stats",
        }
        for page_label, key in pages.items():
            if st.button(page_label, key=f"nav_{key}", use_container_width=True):
                logger.info(f"Navigating to page: {key}")
                st.session_state.page = key
                st.rerun()
        
        # ── Project 2 — RAG AI Assistant ─────────────────────────
        st.markdown(
            "<hr style='border:1px solid rgba(255,255,255,.3);margin:10px 0;'>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='color:#C4B5FD;font-size:.78rem;text-align:center;"
            "font-weight:600;letter-spacing:.08em;'>🤖 AI ASSISTANT</p>",
            unsafe_allow_html=True,
        )
        if st.button("🤖 AI Assistant", key="nav_ai", use_container_width=True):
            st.session_state.page = "AI Assistant"
            st.rerun()

        st.markdown(
            "<hr style='border:1px solid rgba(255,255,255,.3);margin:15px 0;'>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<hr style='border:1px solid rgba(255,255,255,.3);margin:15px 0;'>",
            unsafe_allow_html=True,
        )

        if is_up:
            stats = get_stats()
            if stats:
                logger.debug(f"Stats: {stats.get('templates')} templates, {stats.get('documents_generated')} docs")
                st.markdown("<h3 style='color:white;'>📊 Live Stats</h3>", unsafe_allow_html=True)
                st.metric("Templates", stats.get("templates", 0))
                st.metric("Documents", stats.get("documents_generated", 0))
                st.metric("Jobs Done", stats.get("jobs_completed", 0))

        st.markdown(
            "<div style='color:rgba(255,255,255,.6);text-align:center;font-size:.75rem;margin-top:25px;'>"
            "Powered by Azure OpenAI<br>© 2026 DocForgeHub</div>",
            unsafe_allow_html=True,
        )


# ============================================================
# PAGE: HOME
# ============================================================

def page_home():
    logger.info("Rendering page: Home")
    st.markdown(
        "<h1 class='main-header'>🚀 Welcome to DocForgeHub</h1>", unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align:center;font-size:1.1rem;color:#555;'>"
        "AI-Powered Enterprise Document Generation — PostgreSQL + Azure OpenAI</p>",
        unsafe_allow_html=True,
    )

    stats = get_stats()
    if stats:
        logger.debug(f"Home page stats: {stats}")
    
    c1, c2, c3, c4 = st.columns(4)
    for col, num, lbl in [
        (c1, stats.get("templates", 0) if stats else 0,           "Templates"),
        (c2, stats.get("documents_generated", 0) if stats else 0, "Documents"),
        (c3, stats.get("departments", 0) if stats else len(DEPARTMENTS), "Departments"),
        (c4, stats.get("document_types", 0) if stats else len(ALL_DOC_TYPES), "Doc Types"),
    ]:
        with col:
            st.markdown(
                f"<div class='stat-box'><div class='stat-number'>{num}</div>"
                f"<div class='stat-label'>{lbl}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            "<div class='custom-card'><h3 style='color:#1e3c72;'>🤖 AI Generation</h3>"
            "<p>Azure OpenAI generates production-ready documents tailored to your company context.</p></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            "<div class='custom-card' style='border-left-color:#764ba2'>"
            "<h3 style='color:#1e3c72;'>🗄️ PostgreSQL Backend</h3>"
            "<p>All templates, questionnaires, and documents stored in your PostgreSQL database.</p></div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            "<div class='custom-card' style='border-left-color:#4facfe'>"
            "<h3 style='color:#1e3c72;'>📥 Export Formats</h3>"
            "<p>Download as Word (.docx), PDF (.pdf), or Markdown (.md) with one click.</p></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown(
        f"<h2 class='sub-header'>🏛️ Supported Departments ({len(DEPARTMENTS)})</h2>",
        unsafe_allow_html=True,
    )
    dept_cols = st.columns(3)
    for i, dept in enumerate(DEPARTMENTS):
        with dept_cols[i % 3]:
            doc_count = len(DEPT_DOC_TYPES.get(dept, []))
            st.markdown(
                f"<div class='doc-card' style='padding:12px;'>"
                f"<b style='color:#1e3c72;font-size:.9rem;'>{dept}</b><br>"
                f"<span style='color:#888;font-size:.8rem;'>{doc_count} document types</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✨ Generate New Document", use_container_width=True):
            st.session_state.page = "Generate"
            st.session_state.gen_step = 1
            st.rerun()
    with c2:
        if st.button("📚 View Document Library", use_container_width=True):
            st.session_state.page = "Library"
            st.rerun()

    docs = get_docs()
    if docs:
        st.markdown("<h2 class='sub-header'>🕐 Recent Documents</h2>", unsafe_allow_html=True)
        for doc in docs[:5]:
            badge = "badge-done" if doc.get("status") == "completed" else "badge-draft"
            st.markdown(
                f"<div class='doc-card'><b style='color:#1e3c72;'>#{doc.get('id')} — "
                f"{doc.get('document_type')} | {doc.get('department')}</b><br>"
                f"<span style='color:#999;font-size:.85rem;'>📅 {str(doc.get('created_at',''))[:16]}</span> "
                f"<span class='{badge}'>{str(doc.get('status','')).upper()}</span></div>",
                unsafe_allow_html=True,
            )


# ============================================================
# PAGE: GENERATE
# ============================================================

def page_generate():
    logger.info("Rendering page: Generate")
    st.markdown(
        "<h1 class='main-header'>✨ Generate New Document</h1>", unsafe_allow_html=True
    )
    step = st.session_state.gen_step
    st.progress((step - 1) / 3)
    labels = ["📋 Select Type", "❓ Answer Questions", "🎉 Generate & Review"]
    cols = st.columns(3)
    for i, (col, lbl) in enumerate(zip(cols, labels)):
        with col:
            if i + 1 < step:
                st.markdown(
                    f"<p style='text-align:center;color:#4CAF50;font-weight:600;'>✅ {lbl}</p>",
                    unsafe_allow_html=True,
                )
            elif i + 1 == step:
                st.markdown(
                    f"<p style='text-align:center;color:#667eea;font-weight:600;'>▶️ {lbl}</p>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<p style='text-align:center;color:#999;'>⏺️ {lbl}</p>",
                    unsafe_allow_html=True,
                )
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    
    # Info about regenerate feature
    with st.expander("💡 What is Regenerate?", expanded=False):
        st.markdown("""
        **🔄 Regenerate Document** allows you to create an improved version of your document:
        
        ✨ **Benefits:**
        - Generate fresh content using the same settings and answers
        - Improve quality score and document accuracy  
        - Perfect document doesn't exist on first try - use regenerate to refine
        - Keep your original answers - just improve the AI output
        
        📊 **How it works:**
        1. After generating a document, click **🔄 Regenerate Document**
        2. The AI creates new content based on your previous answers
        3. Compare the quality scores between versions
        4. Use the better version or regenerate again for improvements
        
        💡 **Pro Tips:**
        - Regenerate if you get a low quality score (< 60)
        - You can regenerate multiple times to find the best version
        - All regenerated documents are saved separately
        """)

    # ── Step 1: Select Department & Document Type ──────────────────────────
    if step == 1:
        st.markdown(
            "<h2 class='sub-header'>Step 1: Select Document Type</h2>", unsafe_allow_html=True
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            industry = st.selectbox("🏢 Industry", ["SaaS"], key="s1_ind")
        with c2:
            dept = st.selectbox("🏛️ Department", DEPARTMENTS, key="s1_dept")
        with c3:
            dept_docs = get_doc_types_for_dept(dept)
            dtype = st.selectbox("📄 Document Type", dept_docs, key="s1_type")

        # Preview sections if available
        schema_data = api_get(
            "/questionnaires/schema", params={"department": dept, "document_type": dtype}
        )
        if schema_data and schema_data.get("sections"):
            sections = schema_data["sections"]
            st.markdown(
                f"<div class='info-box'><b>📋 {dtype}</b> — {len(sections)} sections: "
                + ", ".join(f"<code>{s}</code>" for s in sections[:5])
                + ("..." if len(sections) > 5 else "")
                + "</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➡️ Next: Answer Questions", use_container_width=True):
            st.session_state.sel_industry = industry
            st.session_state.sel_dept = dept
            st.session_state.sel_type = dtype
            st.session_state.gen_step = 2
            st.rerun()

    # ── Step 2: Answer Questions ───────────────────────────────────────────
    elif step == 2:
        st.markdown(
            "<h2 class='sub-header'>Step 2: Answer Questions</h2>", unsafe_allow_html=True
        )
        dept  = st.session_state.sel_dept
        dtype = st.session_state.sel_type
        st.markdown(
            f"<div class='info-box'><b>Generating:</b> {dtype} for <b>{dept}</b></div>",
            unsafe_allow_html=True,
        )

        questions = get_questions(dept, dtype)
        answers = {}

        # Group by category
        cats: dict = {}
        for q in questions:
            cats.setdefault(q.get("category", "common"), []).append(q)

        cat_labels = {
            "common":                 "📋 General Questions",
            "metadata":               "🗂 Document Metadata",
            "metadata_questions":     "🗂 Document Metadata",
            "document_type_specific": f"📄 {dtype} — Specific Questions",
            "department_specific":    f"🏛️ {dept} — Specific Questions",
        }

        for cat, qs in cats.items():
            if not qs:
                continue
            st.markdown(
                f"<h3 style='color:#2a5298;margin-top:20px;'>"
                f"{cat_labels.get(cat, cat.replace('_',' ').title())}</h3>",
                unsafe_allow_html=True,
            )
            for q in qs:
                qid   = q.get("id", "")
                qtext = q.get("question", "")
                qtype = q.get("type", "text")
                qreq  = q.get("required", False)
                qopts = q.get("options", [])
                st.markdown(
                    f"<div class='q-block'><b style='color:#1e3c72;'>"
                    f"{'🔴 ' if qreq else ''}{qtext}</b></div>",
                    unsafe_allow_html=True,
                )
                wkey = f"qa_{qid}"
                if qtype == "text":
                    answers[qid] = st.text_input("value", key=wkey, label_visibility="collapsed")
                elif qtype == "textarea":
                    answers[qid] = st.text_area("details", key=wkey, height=90, label_visibility="collapsed")
                elif qtype == "date":
                    answers[qid] = str(st.date_input("date", key=wkey, label_visibility="collapsed"))
                elif qtype == "number":
                    answers[qid] = str(
                        st.number_input("number", key=wkey, step=1, label_visibility="collapsed")
                    )
                elif qtype == "select" and qopts:
                    answers[qid] = st.selectbox(
                        "option", ["(select)"] + qopts, key=wkey, label_visibility="collapsed"
                    )
                elif qtype in ("multi_select", "multiselect") and qopts:
                    answers[qid] = st.multiselect("options", qopts, key=wkey, label_visibility="collapsed")
                else:
                    answers[qid] = st.text_input("value", key=wkey, label_visibility="collapsed")

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state.gen_step = 1
                st.rerun()
        with c2:
            if st.button("🚀 Generate Document", use_container_width=True):
                missing = [
                    q.get("question", "")
                    for q in questions
                    if q.get("required") and not answers.get(q.get("id", ""))
                ]
                if missing:
                    for m in missing:
                        st.error(f"⚠️ Required: {m}")
                else:
                    st.session_state.qa = {
                        k: v for k, v in answers.items() if v and v != "(select)"
                    }
                    st.session_state.gen_step = 3
                    st.rerun()

    # ── Step 3: Generate & Review ──────────────────────────────────────────
    elif step == 3:
        st.markdown(
            "<h2 class='sub-header'>Step 3: Generating Document...</h2>", unsafe_allow_html=True
        )

        if st.session_state.last_doc is None:
            pb = st.progress(0)
            status = st.empty()

            progress_steps = [
                ("Connecting to FastAPI backend...", 0.12),
                ("Loading template from database...", 0.28),
                ("Loading questionnaire schema...", 0.44),
                ("Building AI prompt...", 0.60),
                ("Calling Azure OpenAI (this may take 30-60s)...", 0.78),
                ("Validating and saving document...", 0.92),
            ]
            for txt, pct in progress_steps:
                status.markdown(
                    f"<p style='text-align:center;color:#667eea;font-weight:600;'>{txt}</p>",
                    unsafe_allow_html=True,
                )
                pb.progress(pct)
                time.sleep(0.3)

            # ── Actual API call ────────────────────────────────────────────
            payload = {
                "industry":         st.session_state.sel_industry,
                "department":       st.session_state.sel_dept,
                "document_type":    st.session_state.sel_type,
                "question_answers": st.session_state.qa,
            }
            logger.info(f"Starting document generation - Type: {payload['document_type']}, Dept: {payload['department']}")
            result = api_post("/documents/generate", payload)
            logger.debug(f"Document generation result: {result is not None}")

            pb.progress(1.0)
            status.empty()
            pb.empty()

            if result:
                logger.info(f"Document generated successfully - Doc ID: {result.get('document_id')}")
                st.session_state.last_doc = result
            else:
                logger.error("Document generation failed - No result from API")
                st.error(
                    "❌ Document generation failed.\n\n"
                    "**Common causes:**\n"
                    "- Backend not running (`uvicorn main:app --reload`)\n"
                    "- Azure OpenAI credentials missing in `.env`\n"
                    "- Timeout (check backend logs for the full error)"
                )
                if st.button("⬅️ Try Again", use_container_width=True):
                    st.session_state.gen_step = 2
                    st.rerun()
                return

        doc    = st.session_state.last_doc
        doc_id = doc.get("document_id")
        v      = doc.get("validation", {})
        score  = v.get("score", 0)
        grade  = v.get("grade", "N/A")
        wc     = v.get("word_count", 0)

        st.markdown(
            f"<div class='success-box'>✅ Document Generated Successfully! "
            f"ID: {doc_id} | Job: {str(doc.get('job_id',''))[:8]}...</div>",
            unsafe_allow_html=True,
        )
        
        # Show regeneration info if this is a regenerated document
        if st.session_state.get("_show_comparison"):
            st.info(
                "🎯 This is a **regenerated document** with improved quality! "
                "The AI has generated fresh content using the same parameters. "
                "Compare the quality scores below to see the improvement."
            )


        score_color = "linear-gradient(135deg,#667eea,#764ba2)" if score >= 75 else "linear-gradient(135deg,#f7971e,#ffd200)" if score >= 60 else "linear-gradient(135deg,#f44336,#ff6b6b)"
        perfect_class = "metric-box perfect" if score == 100 else "metric-box"

        
        st.markdown("""
            <style>
            [data-testid="column"] { display:flex; flex-direction:column; }
            [data-testid="column"] > div:first-child { flex:1; display:flex; flex-direction:column; }
            [data-testid="column"] > div:first-child > div { flex:1; }
            [data-testid="column"] > div:first-child > div > div { height:110px !important; }
            </style>
            """, unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4, gap="medium")
        with c1:
            st.markdown(
                f"<div class='{perfect_class}' style='background:{score_color};'>"
                f"<div class='metric-number'>{score}/100</div>"
                f"<div class='metric-label'>Quality Score</div></div>",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"<div class='{perfect_class}' style='background:{score_color};'>"
                f"<div class='metric-number'>{grade}</div>"
                f"<div class='metric-label'>Grade</div></div>",
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"<div class='metric-box'>"
                f"<div class='metric-number'>{wc:,}</div>"
                f"<div class='metric-label'>Words</div></div>",
                unsafe_allow_html=True,
            )
        with c4:
            pc = len(v.get("passed", []))
            ic = len(v.get("issues", []))

            if ic > 0:
                box_bg     = "linear-gradient(135deg,#f44336,#ff6b6b)"
                pass_color = "#ffffff"
                fail_color = "#ffffff"
                label_color= "rgba(255,255,255,0.85)"
                divider    = "rgba(255,255,255,0.4)"
            else:
                box_bg     = "linear-gradient(135deg,#667eea,#764ba2)"
                pass_color = "#ffffff"
                fail_color = "#ffffff"
                label_color= "rgba(255,255,255,0.85)"
                divider    = "rgba(255,255,255,0.4)"

            st.markdown(
                f"<div class='metric-box' style='background:{box_bg};'>"
                f"<div style='display:flex;align-items:center;justify-content:center;gap:14px;margin-bottom:6px;'>"
                f"<div style='text-align:center;'>"
                f"<div style='font-size:1.9rem;font-weight:700;color:{pass_color};line-height:1.2;'>{pc}</div>"
                f"<div style='font-size:0.70rem;letter-spacing:1.8px;text-transform:uppercase;color:{label_color};'>Pass</div>"
                f"</div>"
                f"<div style='width:1px;height:40px;background:{divider};'></div>"
                f"<div style='text-align:center;'>"
                f"<div style='font-size:1.9rem;font-weight:700;color:{fail_color};line-height:1.2;'>{ic}</div>"
                f"<div style='font-size:0.70rem;letter-spacing:1.8px;text-transform:uppercase;color:{label_color};'>Fail</div>"
                f"</div>"
                f"</div>"
                f"<div style='font-size:0.70rem;letter-spacing:1.8px;text-transform:uppercase;color:{label_color};margin-top:2px;'>Checks</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        
        # Display full document with all sections
        st.subheader("📖 Full Document Content")
        doc_content = doc.get("document", "No content available.")
        
        # Create a container with scrollable content
        with st.container():
            st.markdown("""
            <style>
            .document-container {
                max-height: 800px;
                overflow-y: auto;
                padding: 20px;
                background-color: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Display document in markdown with full content
            st.markdown(f"""
            <div class="document-container">
            {doc_content}
            </div>
            """, unsafe_allow_html=True)
        
        # Add a section to view all sections separately
        with st.expander("🔍 View Sections", expanded=False):
            # Split content by headers to show individual sections
            lines = doc_content.split('\n')
            current_section = ""
            section_num = 0
            
            for line in lines:
                if line.startswith('##') and not line.startswith('###'):
                    if current_section and current_section.strip():
                        section_num += 1
                        with st.expander(f"Section {section_num}: {current_section[:50]}..."):
                            st.markdown(current_section)
                    current_section = line
                else:
                    current_section += "\n" + line
        
        with st.expander("📋 Your Submitted Answers"):
            st.json(st.session_state.qa)
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        full_doc = api_get(f"/documents/{doc_id}")
        render_download_buttons(
            doc_id,
            st.session_state.sel_type,
            st.session_state.sel_dept,
            full_doc,
            key_prefix="gen",
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🔄 Regenerate Document", use_container_width=True):
                logger.info(f"User clicked regenerate for document {doc_id}")
                st.session_state["_regen_in_progress"] = True
                with st.spinner("🔄 Regenerating document with improved quality..."):
                    try:
                        regen_result = api_post(f"/documents/regenerate/{doc_id}", {})
                        if regen_result:
                            logger.info(f"Regeneration successful - New Doc ID: {regen_result.get('regenerated_document_id')}")
                            st.session_state.last_doc = {
                                "job_id": regen_result.get("regen_job_id"),
                                "document_id": regen_result.get("regenerated_document_id"),
                                "document": regen_result.get("document"),
                                "validation": regen_result.get("validation", {}),
                            }
                            st.session_state["_regen_in_progress"] = False
                            st.session_state["_show_comparison"] = True
                            st.success(f"✅ Document regenerated! New ID: {regen_result.get('regenerated_document_id')}")
                            st.rerun()
                        else:
                            st.session_state["_regen_in_progress"] = False
                            st.error("❌ Regeneration failed. Please try again.")
                    except Exception as e:
                        st.session_state["_regen_in_progress"] = False
                        logger.error(f"Regeneration error: {str(e)}")
                        st.error(f"❌ Error: {str(e)}")
        
        with c2:
            if st.button("🔄 Generate Another", use_container_width=True):
                st.session_state.gen_step = 1
                st.session_state.last_doc = None
                st.session_state.qa = {}
                st.rerun()
        
        with c3:
            if st.button("📚 Go to Library", use_container_width=True):
                st.session_state.page = "Library"
                st.session_state.gen_step = 1
                st.session_state.last_doc = None
                st.rerun()


# ============================================================
# PAGE: LIBRARY
# ============================================================


@st.dialog("🗑️ Delete Document")
def confirm_delete_dialog(doc_id, doc_type):
    """GitHub-style centered delete confirmation dialog."""
    st.markdown(f"""
    <div style="text-align:center; padding:10px 0;">
        <div style="font-size:3rem;">🗑️</div>
        <h3 style="color:#24292f; margin:8px 0;">Delete this document?</h3>
        <p style="color:#57606a; font-size:0.9rem;">
            This action <strong>cannot be undone</strong>.<br>
            This will permanently delete this document.
        </p>
    </div>
    <div style="
        background:#fff8f0;
        border:1px solid #f5a623;
        border-radius:8px;
        padding:12px 16px;
        margin:12px 0;
        font-size:0.85rem;
        color:#633d00;
    ">
        To confirm, type <code style="
            background:#f0f0f0;
            padding:2px 6px;
            border-radius:4px;
            font-weight:700;
            color:#d73a49;
        ">{doc_type}</code> in the box below
    </div>
    """, unsafe_allow_html=True)

    confirm_input = st.text_input(
        "",
        placeholder=f"Type: {doc_type}",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns(2)
    with col1:
        delete_disabled = confirm_input.strip() != doc_type.strip()
        if st.button(
            "🗑️ Delete this document",
            use_container_width=True,
            type="primary",
            disabled=delete_disabled,
        ):
            st.session_state[f"do_delete_{doc_id}"] = True
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

def page_library():
    logger.info("Rendering page: Library")
    st.markdown("<h1 class='main-header'>📚 Document Library</h1>", unsafe_allow_html=True)
    
    # ✅ Export Feature Info
    # with st.info():
    # CORRECT
    st.markdown(
            "**💡 Export Tip:** If an export times out, click the **🔄 Regenerate** button to retry. "
            "Large documents may take time to process. The system will automatically retry up to 2 times with increased wait times."
        )
    
    c1, c2, c3 = st.columns(3)
    with c1:
        f_dept = st.selectbox("Filter Department", ["All"] + DEPARTMENTS, key="lib_d")
    with c2:
        dept_types = DEPT_DOC_TYPES.get(f_dept, []) if f_dept != "All" else ALL_DOC_TYPES
        f_type = st.selectbox("Filter Document Type", ["All"] + dept_types, key="lib_t")
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", use_container_width=True):
            logger.debug("Refreshing document cache")
            get_docs.clear()
            st.rerun()

    logger.debug(f"Library filters: Department={f_dept}, Type={f_type}")
    docs = get_docs(
        dept=f_dept  if f_dept  != "All" else None,
        dtype=f_type if f_type  != "All" else None,
    )
    logger.debug(f"Library loaded {len(docs)} documents")
    st.markdown(
        f"<p style='color:#666;'><b>{len(docs)}</b> documents found</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    if not docs:
        st.markdown(
            "<div class='info-box'><h3>📭 No Documents Yet</h3>"
            "<p>Generate your first document using the Generate page.</p></div>",
            unsafe_allow_html=True,
        )
        if st.button("✨ Generate Document", use_container_width=True):
            st.session_state.page = "Generate"
            st.rerun()
        return

    for doc in docs:
        doc_id = str(doc.get("id", ""))
        badge  = "badge-done" if doc.get("status") == "completed" else "badge-draft"
        st.markdown(
            f"<div class='doc-card'>"
            f"<b style='color:#1e3c72;font-size:1.05rem;'>#{doc.get('id')} — {doc.get('document_type')}</b><br>"
            f"<span style='color:#666;'>🏛️ {doc.get('department')} | 🏢 {doc.get('industry')}</span><br>"
            f"<span style='color:#999;font-size:.85rem;'>📅 {str(doc.get('created_at',''))[:16]}</span> "
            f"<span class='{badge}' style='margin-left:10px;'>{str(doc.get('status','')).upper()}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button(f"📖 View #{doc.get('id')}", key=f"btn_view_{doc_id}", use_container_width=True):
                st.session_state[f"view_{doc_id}"] = not st.session_state.get(f"view_{doc_id}", False)

        # ✅ Columns ke BAHAR render karo — full width milega
        if st.session_state.get(f"view_{doc_id}"):
            full = api_get(f"/documents/{doc.get('id')}")
            if full:
                meta = full.get("metadata", {})
                st.markdown(
                    f"<div class='doc-card' style='margin-top:8px;'>"
                    f"<span style='color:#666;font-size:.85rem;'>"
                    f"📄 <b>#{doc.get('id')} — {full.get('document_type')}</b> &nbsp;|&nbsp; "
                    f"🏛️ {full.get('department')} &nbsp;|&nbsp; "
                    f"📝 {meta.get('word_count', 'N/A')} words"
                    f"</span></div>",
                    unsafe_allow_html=True,
                )
                st.markdown("---")
                import re as _re
                _raw  = full.get("generated_content", "No content available")
                _clean = _re.sub(r'<[^>]+>', '', _raw)
                st.markdown(_clean)
                if st.button(f"✖ Close View #{doc_id}", key=f"close_{doc_id}"):
                    st.session_state[f"view_{doc_id}"] = False
                    st.rerun()
        with c2:
            if st.button(
                f"🔄 Regenerate #{doc.get('id')}", key=f"regen_{doc_id}", use_container_width=True
            ):
                doc_id_val = doc.get('id')
                logger.info(f"User clicked regenerate for document {doc_id_val} from library")
                with st.spinner("🔄 Regenerating document..."):
                    try:
                        regen_result = api_post(f"/documents/regenerate/{doc_id_val}", {})
                        if regen_result:
                            logger.info(f"Regeneration successful - New Doc ID: {regen_result.get('regenerated_document_id')}")
                            st.success(f"✅ Regenerated! New ID: {regen_result.get('regenerated_document_id')}")
                            get_docs.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Regeneration failed.")
                    except Exception as e:
                        logger.error(f"Regeneration error: {str(e)}")
                        st.error(f"❌ Error: {str(e)}")
        with c3:
            if st.button(
                f"🗑️ Delete #{doc.get('id')}", key=f"del_{doc_id}", use_container_width=True
            ):
                confirm_delete_dialog(doc_id, doc.get("document_type", ""))

            # Handle actual deletion after dialog confirm
            if st.session_state.get(f"do_delete_{doc_id}"):
                st.session_state.pop(f"do_delete_{doc_id}", None)
                if api_delete(f"/documents/{doc.get('id')}"):
                    logger.info(f"Document deleted — ID:{doc.get('id')} | Type:{doc.get('document_type')} | Dept:{doc.get('department')}")
                    st.success("✅ Deleted!")
                    get_docs.clear()
                    get_stats.clear()
                    st.rerun()
        # Download toggle section
        st.markdown(f"<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        
        if st.session_state.get(f"show_dl_{doc_id}"):
            render_download_buttons(
                doc.get("id"),
                doc.get("document_type", ""),
                doc.get("department", ""),
                key_prefix=f"lib_{doc_id}",
            )
        else:
            if st.button(f"📥 Show Download Options", key=f"dl_show_{doc_id}", use_container_width=True):
                st.session_state[f"show_dl_{doc_id}"] = True
                st.rerun()


# ============================================================
# PAGE: TEMPLATES
# ============================================================

# def page_templates():
#     logger.info("Rendering page: Templates")
#     st.markdown("<h1 class='main-header'>🗂 Templates</h1>", unsafe_allow_html=True)
#     c1, c2 = st.columns(2)
#     with c1:
#         fd = st.selectbox("Department", ["All"] + DEPARTMENTS, key="t_d")
#     with c2:
#         dept_types = DEPT_DOC_TYPES.get(fd, []) if fd != "All" else ALL_DOC_TYPES
#         ft = st.selectbox("Document Type", ["All"] + dept_types, key="t_t")

#     params = {}
#     if fd != "All":
#         params["department"] = fd
#     if ft != "All":
#         params["document_type"] = ft

#     templates = api_get("/templates/", params=params) or []
#     # Handle wrapped response
#     if isinstance(templates, dict):
#         templates = templates.get("templates", templates.get("items", []))

#     st.markdown(
#         f"<p style='color:#666;'><b>{len(templates)}</b> templates</p>",
#         unsafe_allow_html=True,
#     )
#     st.markdown("<hr class='divider'>", unsafe_allow_html=True)

#     if not templates:
#         st.info("ℹ️ API offline or no templates found — showing local schema preview.")
#         show_depts = [fd] if fd != "All" else DEPARTMENTS
#         for dept in show_depts:
#             with st.expander(
#                 f"🏛️ {dept} ({len(DEPT_DOC_TYPES.get(dept, []))} templates)"
#             ):
#                 for dt in DEPT_DOC_TYPES.get(dept, []):
#                     st.markdown(f"  • **{dt}**")
#         return

#     for tmpl in templates:
#         with st.expander(
#             f"🗂 {tmpl.get('department')} — {tmpl.get('document_type')}  (v{tmpl.get('version', '1.0')})"
#         ):
#             full = api_get(f"/templates/{tmpl.get('id')}")
#             if full and full.get("structure"):
#                 sections = full["structure"].get("sections", [])
#                 st.markdown(f"**Sections ({len(sections)}):**")
#                 for i, s in enumerate(sections, 1):
#                     st.markdown(f"  `{i}.` {s}")
#             st.markdown(f"**Active:** {'✅' if tmpl.get('is_active') else '❌'}")

def page_templates():
    logger.info("Rendering page: Templates")
    st.markdown("<h1 class='main-header'>🗂️ Templates</h1>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        fd = st.selectbox("Department", ["All"] + DEPARTMENTS, key="t_d")
    with c2:
        dept_types = DEPT_DOC_TYPES.get(fd, []) if fd != "All" else ALL_DOC_TYPES
        ft = st.selectbox("Document Type", ["All"] + dept_types, key="t_t")

    params = {}
    if fd != "All": params["department"] = fd
    if ft != "All": params["document_type"] = ft

    templates = api_get("/templates/", params=params) or []
    if isinstance(templates, dict):
        templates = templates.get("templates", templates.get("items", []))

    st.markdown(
        f"<p style='color:#666;'><b>{len(templates)}</b> templates</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    if not templates:
        st.info("ℹ️ API offline or no templates found.")
        return

    for tmpl in templates:
        tmpl_id  = str(tmpl.get("id"))
        edit_key = f"edit_mode_{tmpl_id}"
        sess_key = f"sections_{tmpl_id}"

        with st.expander(
            f"🗂️ {tmpl.get('department')} — {tmpl.get('document_type')}  (v{tmpl.get('version','1.0')})"
        ):
            full = api_get(f"/templates/{tmpl_id}")
            if not full or not full.get("structure"):
                st.warning("Could not load template structure.")
                continue

            db_sections = full["structure"].get("sections", [])

            # ── Top bar ───────────────────────────────────────────────────
            col_title, col_btn = st.columns([6, 1])
            with col_title:
                st.markdown(f"**Sections ({len(db_sections)}):**")
            with col_btn:
                if st.button(
                    "✏️ Edit" if not st.session_state.get(edit_key) else "✖ Cancel",
                    key=f"toggle_{tmpl_id}",
                    use_container_width=True,
                ):
                    is_opening = not st.session_state.get(edit_key, False)
                    st.session_state[edit_key] = is_opening
                    if is_opening:
                        # Fresh copy from DB only when opening
                        st.session_state[sess_key] = db_sections.copy()
                    else:
                        st.session_state.pop(sess_key, None)
                    st.rerun()

            # ── VIEW MODE ─────────────────────────────────────────────────
            if not st.session_state.get(edit_key):
                for i, s in enumerate(db_sections, 1):
                    st.markdown(f"  `{i}.` {s}")
                st.markdown(
                    f"<br><span style='color:#666;font-size:.85rem;'>"
                    f"Active: {'✅' if tmpl.get('is_active') else '❌'}</span>",
                    unsafe_allow_html=True,
                )

            # ── EDIT MODE ─────────────────────────────────────────────────
            else:
                if sess_key not in st.session_state:
                    st.session_state[sess_key] = db_sections.copy()

                st.markdown(
                    "<div class='info-box' style='padding:10px 14px;font-size:.85rem;'>"
                    "✏️ Edit mode — add, remove or reorder sections.</div>",
                    unsafe_allow_html=True,
                )
                st.markdown("")

                # ── Sync text_input values INTO session state ─────────────
                # Pehle har input ka key session_state mein set karo
                for i, sec in enumerate(st.session_state[sess_key]):
                    input_key = f"sec_{tmpl_id}_{i}"
                    if input_key not in st.session_state:
                        st.session_state[input_key] = sec

                # ── Render sections ───────────────────────────────────────
                remove_idx = None
                for i in range(len(st.session_state[sess_key])):
                    input_key = f"sec_{tmpl_id}_{i}"
                    r1, r2 = st.columns([9, 1])
                    with r1:
                        # ✅ KEY ONLY — no value= parameter
                        st.text_input(
                            f"s{i}",
                            key=input_key,
                            label_visibility="collapsed",
                        )
                    with r2:
                        if st.button("🗑️", key=f"del_{tmpl_id}_{i}"):
                            remove_idx = i

                # ── Remove AFTER loop ────────────────────────────────────
                if remove_idx is not None:
                    # Sync edited values back before removing
                    for i in range(len(st.session_state[sess_key])):
                        input_key = f"sec_{tmpl_id}_{i}"
                        if input_key in st.session_state:
                            st.session_state[sess_key][i] = st.session_state[input_key]
                    st.session_state[sess_key].pop(remove_idx)
                    # Clear all input keys to force re-render
                    for i in range(len(st.session_state[sess_key]) + 1):
                        st.session_state.pop(f"sec_{tmpl_id}_{i}", None)
                    st.rerun()

                st.markdown("")

                # ── Add at END ───────────────────────────────────────────
                st.markdown("**➕ Add New Section:**")
                a1, a2 = st.columns([8, 2])
                with a1:
                    new_sec = st.text_input(
                        "add_input",
                        placeholder="e.g. Risk_Assessment",
                        key=f"new_sec_{tmpl_id}",
                        label_visibility="collapsed",
                    )
                with a2:
                    if st.button("Add", key=f"add_{tmpl_id}", use_container_width=True):
                        val = new_sec.strip()
                        if not val:
                            st.warning("Section name cannot be empty.")
                        elif val in st.session_state[sess_key]:
                            st.error(f"'{val}' already exists!")
                        else:
                            # Sync current edits before adding
                            for i in range(len(st.session_state[sess_key])):
                                input_key = f"sec_{tmpl_id}_{i}"
                                if input_key in st.session_state:
                                    st.session_state[sess_key][i] = st.session_state[input_key]
                            st.session_state[sess_key].append(val)
                            # Clear input keys
                            for i in range(len(st.session_state[sess_key])):
                                st.session_state.pop(f"sec_{tmpl_id}_{i}", None)
                            st.session_state.pop(f"new_sec_{tmpl_id}", None)
                            st.rerun()

                # ── Insert at POSITION ────────────────────────────────────
                st.markdown("**📍 Insert Section at Position:**")
                p1, p2, p3 = st.columns([5, 2, 2])
                with p1:
                    ins_name = st.text_input(
                        "ins_input",
                        placeholder="e.g. Executive_Summary",
                        key=f"mid_sec_{tmpl_id}",
                        label_visibility="collapsed",
                    )
                with p2:
                    total = len(st.session_state[sess_key])
                    ins_pos = st.number_input(
                        "pos_input",
                        min_value=1,
                        max_value=total + 1,
                        value=total + 1,
                        step=1,
                        key=f"pos_{tmpl_id}",
                        label_visibility="collapsed",
                    )
                with p3:
                    if st.button("Insert", key=f"insert_{tmpl_id}", use_container_width=True):
                        val = ins_name.strip()
                        if not val:
                            st.warning("Section name required.")
                        elif val in st.session_state[sess_key]:
                            st.error(f"'{val}' already exists!")
                        else:
                            # Sync current edits before inserting
                            for i in range(len(st.session_state[sess_key])):
                                input_key = f"sec_{tmpl_id}_{i}"
                                if input_key in st.session_state:
                                    st.session_state[sess_key][i] = st.session_state[input_key]
                            st.session_state[sess_key].insert(int(ins_pos) - 1, val)
                            # Clear input keys
                            for i in range(len(st.session_state[sess_key])):
                                st.session_state.pop(f"sec_{tmpl_id}_{i}", None)
                            st.session_state.pop(f"mid_sec_{tmpl_id}", None)
                            st.rerun()

                st.markdown("<hr class='divider'>", unsafe_allow_html=True)

                # ── Save / Cancel ─────────────────────────────────────────
                s1, s2 = st.columns(2)
                with s1:
                    if st.button("💾 Save to Database", key=f"save_{tmpl_id}", use_container_width=True):
                        # Sync all text inputs before saving
                        for i in range(len(st.session_state[sess_key])):
                            input_key = f"sec_{tmpl_id}_{i}"
                            if input_key in st.session_state:
                                st.session_state[sess_key][i] = st.session_state[input_key]

                        seen  = set()
                        final = []
                        for s in st.session_state[sess_key]:
                            s = s.strip()
                            if s and s.lower() not in seen:
                                final.append(s)
                                seen.add(s.lower())

                        if not final:
                            st.error("Cannot save — at least 1 section required.")
                        else:
                            result = api_post(
                                f"/templates/{tmpl_id}/sections",
                                {"sections": final},
                                method="PUT",
                            )
                            if result and result.get("success"):
                                st.success(f"✅ Saved! {len(final)} sections updated.")
                                st.session_state[edit_key] = False
                                st.session_state.pop(sess_key, None)
                                for i in range(50):
                                    st.session_state.pop(f"sec_{tmpl_id}_{i}", None)
                                st.rerun()
                            else:
                                st.error("❌ Save failed — check API connection.")
                with s2:
                    if st.button("✖ Cancel", key=f"cancel_{tmpl_id}", use_container_width=True):
                        st.session_state[edit_key] = False
                        st.session_state.pop(sess_key, None)
                        for i in range(50):
                            st.session_state.pop(f"sec_{tmpl_id}_{i}", None)
                        st.rerun()
# ============================================================
# PAGE: QUESTIONNAIRES
# ============================================================

def page_questionnaires():
    logger.info("Rendering page: Questionnaires")
    st.markdown("<h1 class='main-header'>❓ Questionnaires</h1>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        dept = st.selectbox("Department", DEPARTMENTS, key="qa_d")
    with c2:
        dept_types = get_doc_types_for_dept(dept)
        dtype = st.selectbox("Document Type", dept_types, key="qa_t")

    if st.button("🔍 Load Questions", use_container_width=True):
        logger.debug(f"Loading questions for {dept} - {dtype}")
        qs = get_questions(dept, dtype)
        if not qs:
            st.warning("No questionnaire found for this combination.")
        else:
            st.markdown(
                f"<div class='success-box'>✅ {len(qs)} questions for {dept} — {dtype}</div>",
                unsafe_allow_html=True,
            )
            cats: dict = {}
            for q in qs:
                cats.setdefault(q.get("category", "common"), []).append(q)

            cat_labels = {
                "common":                 "📋 Common / General",
                "metadata":               "🗂 Document Metadata",
                "metadata_questions":     "🗂 Document Metadata",
                "document_type_specific": f"📄 {dtype} — Specific",
                "department_specific":    f"🏛️ {dept} — Specific",
            }

            for cat, cqs in cats.items():
                st.markdown(
                    f"<h3 style='color:#2a5298;margin-top:15px;'>"
                    f"{cat_labels.get(cat, cat.replace('_',' ').title())} ({len(cqs)})</h3>",
                    unsafe_allow_html=True,
                )
                for q in cqs:
                    req = "🔴 Required" if q.get("required") else "⚪ Optional"
                    opts_str = (
                        f" | Options: {', '.join(q['options'])}" if q.get("options") else ""
                    )
                    st.markdown(
                        f"<div class='q-block'>"
                        f"<b>{q.get('question','')}</b><br>"
                        f"<span style='color:#888;font-size:.85rem;'>"
                        f"Type: {q.get('type','')} | {req}{opts_str}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown(
        f"<h3 style='color:#2a5298;'>📋 Schema Sections for: {dtype}</h3>",
        unsafe_allow_html=True,
    )
    schema_data = api_get(
        "/questionnaires/schema", params={"department": dept, "document_type": dtype}
    )
    if schema_data and schema_data.get("sections"):
        for i, s in enumerate(schema_data["sections"], 1):
            st.markdown(f"`{i}.` **{s}**")
    else:
        st.info("Schema sections will appear here when the API is connected.")


# ============================================================
# PAGE: NOTION
# ============================================================


def page_notion():
    logger.info("Rendering page: Publish to Notion")
    st.markdown("<h1 class='main-header'>🚀 Publish to Notion</h1>", unsafe_allow_html=True)

    st.markdown("<h2 class='sub-header'>🔑 Step 1: Connect Notion</h2>", unsafe_allow_html=True)
    with st.expander("ℹ️ How to get your Notion Token"):
        st.markdown(
            """
1. Go to **https://www.notion.so/my-integrations** → New Integration → copy token (`secret_...`)
2. Open your Notion database → click `...` → **Connections** → Add your integration
3. Copy the **Database ID** from the URL: `notion.so/workspace/`**`DATABASE_ID`**`?v=...`
            """
        )

    import os
    from dotenv import load_dotenv
    load_dotenv()
    # Auto-load from .env — user sirf Publish button click kare
    token     = os.getenv("NOTION_TOKEN", "")
    db_id_raw = os.getenv("NOTION_DATABASE_ID", "")
    if token and db_id_raw:
        st.success("✅ Notion Connected — Click Publish to publish documents")
    else:
        st.warning("⚠️ Notion credentials not found in .env — enter manually:")
        token     = st.text_input("🔐 Integration Token", type="password", placeholder="secret_xxxx", key="notion_token")
        db_id_raw = st.text_input("📋 Database ID", placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", key="notion_db_id")
    db_id     = _clean_db_id(db_id_raw) if db_id_raw else ""

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔍 Test Token", use_container_width=True):
            if not token:
                st.error("Enter your integration token first.")
            else:
                logger.info("Testing Notion token")
                with st.spinner("Testing..."):
                    ok, msg = notion_test(token)
                logger.debug(f"Notion token test result: {ok} - {msg}")
                st.success(f"✅ {msg}") if ok else st.error(f"❌ {msg}")
    with c2:
        if st.button("🗄️ Test Database Access", use_container_width=True):
            if not token or not db_id:
                st.error("Enter both token and Database ID first.")
            else:
                logger.info(f"Testing Notion database access: {db_id}")
                with st.spinner("Checking database..."):
                    ok, msg = notion_test_database(token, db_id)
                logger.debug(f"Notion database test result: {ok} - {msg}")
                st.success(f"✅ {msg}") if ok else st.error(f"❌ {msg}")

    if token and st.button("🔍 Auto-detect My Databases", use_container_width=True):
        logger.info("Auto-detecting Notion databases")
        with st.spinner("Searching..."):
            dbs = notion_databases(token)
        logger.debug(f"Found {len(dbs)} Notion databases")
        if dbs:
            st.markdown(
                f"<div class='info-box'>Found <b>{len(dbs)}</b> databases — copy an ID above:</div>",
                unsafe_allow_html=True,
            )
            for db in dbs:
                st.code(f"{db['name']}\nID: {db['id']}", language="text")
        else:
            st.warning(
                "No databases found. Open your DB → `...` → Connections → add your integration."
            )

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown("<h2 class='sub-header'>📄 Step 2: Select & Publish</h2>", unsafe_allow_html=True)

    docs = get_docs()
    if not docs:
        st.info("No documents yet. Generate some first.")
        return

    if "notion_published" not in st.session_state:
        st.session_state.notion_published = {}

    pub_count = len([d for d in docs if d.get('notion_page_id', '')])
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"<div class='stat-box'><div class='stat-number'>{len(docs)}</div>"
            f"<div class='stat-label'>Total Docs</div></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div class='stat-box'><div class='stat-number'>{len(docs)-pub_count}</div>"
            f"<div class='stat-label'>Unpublished</div></div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"<div class='stat-box'><div class='stat-number'>{pub_count}</div>"
            f"<div class='stat-label'>Published</div></div>",
            unsafe_allow_html=True,
        )

        unpublished = [d for d in docs if not d.get('notion_page_id', '')]

    if unpublished and st.button(
        f"🚀 Publish All ({len(unpublished)}) to Notion", use_container_width=True
    ):
        if not token or not db_id:
            st.error("Enter Token and Database ID first.")
        else:
            pb = st.progress(0)
            status = st.empty()
            errors = []
            for idx, d in enumerate(unpublished):
                status.markdown(
                    f"<p style='text-align:center;'>Publishing #{d.get('id')}: "
                    f"{d.get('document_type')} — {d.get('department')}...</p>",
                    unsafe_allow_html=True,
                )
                full = api_get(f"/documents/{d.get('id')}")
                if full:
                    content = full.get("generated_content", "")
                    if not content.strip():
                        errors.append(f"Doc #{d.get('id')}: empty content, skipped")
                    else:
                        pdf_bytes = fetch_file(d.get("id"), "pdf")
                        ok, url, pid = notion_publish(doc=full, doc_type=full.get('document_type'), content=content, database_id=db_id, token=token, pdf_bytes=None)
                        if ok:
                            # Save to DB so no duplicate on next publish
                            api_post(f"/documents/{d.get('id')}/mark-notion", {
                                "notion_page_id": pid,
                                "notion_url": url,
                                "notion_version": 1,
                            })
                            st.session_state.notion_published[str(d.get("id"))] = {
                                "url": url, "pid": pid,
                                "title": f"{d.get('document_type')} — {d.get('department')}",
                            }
                        else:
                            errors.append(f"Doc #{d.get('id')}: {url}")
                pb.progress((idx + 1) / len(unpublished))
            status.empty()
            if errors:
                st.error("Some failed:\n" + "\n".join(errors))
            else:
                st.markdown(
                    f"<div class='success-box'>🎉 All {len(unpublished)} documents published!</div>",
                    unsafe_allow_html=True,
                )
            st.rerun()

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    for doc in docs:
        doc_id   = str(doc.get("id", ""))
        existing_page_id = doc.get('notion_page_id', '') or ''
        existing_version = doc.get('notion_version', 1) or 1
        existing_url     = doc.get('notion_url', '') or ''
     # ✅ Fast check — sirf DB se, Notion API call nahi
        is_already_published = bool(existing_page_id)

        # Notion sync button — user manually click kare tab hi check karo
        if is_already_published and token:
            sync_key = f"sync_{doc_id}"
            if st.session_state.get(sync_key):
                # Tab Notion se verify karo
                from services.notion_service import check_notion_page_exists
                still_exists = check_notion_page_exists(existing_page_id, token)
                if not still_exists:
                    is_already_published = False
                    api_post(f"/documents/{doc.get('id')}/mark-notion", {
                        "notion_page_id": "",
                        "notion_url": "",
                        "notion_version": 0,
                    }, method="PUT")
                st.session_state.pop(sync_key, None)
        is_pub   = doc_id in st.session_state.notion_published
        pub_info = st.session_state.notion_published.get(doc_id, {})
        notion_url = existing_url

        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            link_html = (
                f'<a href="{notion_url}" target="_blank" '
                f'style="color:#4CAF50;font-weight:600;text-decoration:none;">🔗 Open in Notion →</a>'
                if is_pub and notion_url else ""
            )
            st.markdown(
                f"<div class='doc-card'>"
                f"<b style='color:#1e3c72;'>#{doc.get('id')} — {doc.get('document_type')}</b><br>"
                f"<span style='color:#666;font-size:.9rem;'>🏛️ {doc.get('department')}</span><br>"
                f"{link_html}</div>",
                unsafe_allow_html=True,
            )
            if is_pub and notion_url:
                st.text_input(
                    "📋 Full Notion URL :",
                    value=notion_url,
                    key=f"url_{doc_id}",
                )

        with c2:
            if is_already_published:
                st.markdown(
                    "<div style='background:#4CAF50;padding:8px;border-radius:8px;"
                    "text-align:center;color:white;font-weight:600;'>✅ Published</div>",
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
                if existing_url:
                    st.link_button(
                        "🔗 Open in Notion",
                        url=existing_url,
                        use_container_width=True,
                    )
            else:
                # ✅ NOT published — show badge + publish button
                st.markdown(
                    "<div style='background:linear-gradient(135deg,#667eea,#764ba2);padding:8px;border-radius:8px;"
                    "text-align:center;color:white;font-weight:600;margin-top:8px;'>"
                    "📤 Not Published</div>",
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
                if st.button(f"🚀 Publish #{doc.get('id')}",
                            key=f"pub_{doc_id}",
                            use_container_width=True):
                    if not token or not db_id:
                        st.error("Enter Token and Database ID first.")
                    else:
                        with st.spinner(f"Publishing #{doc.get('id')}..."):
                            full = api_get(f"/documents/{doc.get('id')}")
                            if full:
                                content = full.get("generated_content", "")
                                if not content.strip():
                                    st.error(f"❌ Doc #{doc.get('id')} has no content.")
                                else:
                                    ok, url, pid = notion_publish(
                                        doc=full,
                                        doc_type=doc.get("document_type"),
                                        content=content,
                                        database_id=db_id,
                                        token=token,
                                        pdf_bytes=None,
                                    )
                                    if ok:
                                        api_post(f"/documents/{doc.get('id')}/mark-notion", {
                                            "notion_page_id": pid,
                                            "notion_url": url,
                                            "notion_version": 1,
                                        })
                                        st.success("✅ Published!")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {url}")
        with c3:
            if st.button(
                f"⬇️ Download #{doc.get('id')}", key=f"ndl_{doc_id}", use_container_width=True
            ):
                st.session_state[f"notion_dl_{doc_id}"] = not st.session_state.get(
                    f"notion_dl_{doc_id}", False
                )
        if st.session_state.get(f"notion_dl_{doc_id}"):
            render_download_buttons(
                doc.get("id"),
                doc.get("document_type", ""),
                doc.get("department", ""),
                key_prefix=f"notion_{doc_id}",
            )


# ============================================================
# PAGE: STATS
# ============================================================

def page_stats():
    logger.info("Rendering page: Stats")
    st.markdown("<h1 class='main-header'>📊 System Stats</h1>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Stats"):
        logger.debug("Refreshing stats cache")
        get_stats.clear()
        st.rerun()

    logger.debug("Fetching health status")
    health = api_get("/system/health")
    if health:
        db_status = health.get("database")
        logger.debug(f"Database status: {db_status}")
        color = "#4CAF50" if db_status == "connected" else "#f44336"
        st.markdown(
            f"<div style='background:{color};padding:12px;border-radius:10px;color:white;"
            f"text-align:center;font-weight:600;margin-bottom:18px;'>"
            f"Database: {db_status.upper()}</div>",
            unsafe_allow_html=True,
        )

    stats = get_stats()
    if stats:
        c1, c2, c3, c4 = st.columns(4)
        for col, lbl, key in [
            (c1, "📋 Templates",     "templates"),
            (c2, "❓ Questionnaires","questionnaires"),
            (c3, "📄 Documents",     "documents_generated"),
            (c4, "⚙️ Jobs",          "total_jobs"),
        ]:
            with col:
                st.metric(lbl, stats.get(key, 0))

        c1, c2, c3, c4 = st.columns(4)
        for col, lbl, key in [
            (c1, "✅ Completed", "jobs_completed"),
            (c2, "❌ Failed",    "jobs_failed"),
            (c3, "🏢 Depts",    "departments"),
            (c4, "📁 Types",    "document_types"),
        ]:
            with col:
                st.metric(lbl, stats.get(key, 0))
    else:
        st.markdown(
            "<h3 style='color:#2a5298;'>📊 Local Schema Stats (offline mode)</h3>",
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("🏢 Departments", len(DEPARTMENTS))
        with c2:
            st.metric("📁 Total Doc Types", len(ALL_DOC_TYPES))
        with c3:
            st.metric("📋 Avg per Dept", 10)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown(
        "<h2 class='sub-header'>🏛️ Department — Document  Map</h2>",
        unsafe_allow_html=True,
    )
    rows = [
        {"Department": dept, "Document ": doc}
        for dept, docs in DEPT_DOC_TYPES.items()
        for doc in docs
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=400)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown("<h2 class='sub-header'>⚙️ Recent Jobs</h2>", unsafe_allow_html=True)

    # jobs_data = api_get("/documents/jobs") or []
    # jobs_data = requests.get(f"{API_BASE_URL}/documents/jobs", timeout=10).json() or []
    # if isinstance(jobs_data, dict):
    #     jobs_data = jobs_data.get("jobs", jobs_data.get("items", []))
    # FIND:
    jobs_data = requests.get(
        f"{API_BASE_URL}/documents/jobs", timeout=10
    ).json() or []

    # REPLACE WITH — only show jobs where document still exists:
    jobs_data = requests.get(
        f"{API_BASE_URL}/documents/jobs", timeout=10
    ).json() or []
    if isinstance(jobs_data, list):
        jobs_data = [j for j in jobs_data if j.get("result_doc_id") is not None]
    if jobs_data:
        rows = [
            {
                "Job ID":     str(j.get("job_id", ""))[:12] + "...",
                "Status":     j.get("status", ""),
                "Type":       j.get("document_type", ""),
                "Department": j.get("department", ""),
                "Started":    str(j.get("started_at", ""))[:16],
            }
            for j in jobs_data
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("No jobs yet or backend offline.")

# # ============================================================
# # PAGE: AI ASSISTANT (RAG Chat)
# # ============================================================
# def page_rag_chat():
#     import uuid
#     st.markdown("<h1 class='main-header'>🤖 AI Assistant</h1>", unsafe_allow_html=True)
#     st.markdown(
#         "<p style='text-align:center;color:#666;'>Ask questions about your documents "
#         "— grounded answers with citations from your Notion knowledge base</p>",
#         unsafe_allow_html=True,
#     )
#     st.markdown("<hr class='divider'>", unsafe_allow_html=True)

#     if "rag_session_id"   not in st.session_state:
#         st.session_state.rag_session_id   = str(uuid.uuid4())[:8]
#     if "rag_chat_history" not in st.session_state:
#         st.session_state.rag_chat_history = []

#     # ── Filters ───────────────────────────────────────────────
#     c1, c2 = st.columns(2)
#     with c1:
#         sel_dept = st.selectbox(
#             "Department filter",
#             ["All"] + DEPARTMENTS,
#             key="rag_dept",
#             label_visibility="collapsed",
#         )
#     with c2:
#         sel_type = st.selectbox(
#             "Doc Type filter",
#             ["All"] + ALL_DOC_TYPES,
#             key="rag_type",
#             label_visibility="collapsed",
#         )

#     filters = {}
#     if sel_dept != "All": filters["department"] = sel_dept
#     if sel_type != "All": filters["doc_type"]   = sel_type

#     # ── Chat history ──────────────────────────────────────────
#     for msg in st.session_state.rag_chat_history:
#         if msg["role"] == "user":
#             st.markdown(
#                 f"<div style='background:#E3F2FD;border-radius:12px 12px 4px 12px;"
#                 f"padding:12px 16px;margin:8px 0;border-left:4px solid #1976D2;'>"
#                 f"👤 <b>You:</b> {msg['content']}</div>",
#                 unsafe_allow_html=True,
#             )
#         else:
#             st.markdown(
#                 f"<div style='background:#F3E5F5;border-radius:12px 12px 12px 4px;"
#                 f"padding:12px 16px;margin:8px 0;border-left:4px solid #7B1FA2;'>"
#                 f"🤖 <b>DocForge AI:</b><br>{msg['content']}</div>",
#                 unsafe_allow_html=True,
#             )
#             if msg.get("citations"):
#                 with st.expander("📎 Sources", expanded=False):
#                     for cit in msg["citations"]:
#                         st.markdown(
#                             f"<div class='q-block' style='background:#E8F5E9;"
#                             f"border-left-color:#4CAF50;'>📄 {cit}</div>",
#                             unsafe_allow_html=True,
#                         )

#     # ── Input ─────────────────────────────────────────────────
#     col_q, col_btn = st.columns([8, 2])
#     with col_q:
#         question = st.text_input(
#             "Ask",
#             placeholder='e.g. "What are NDA confidentiality obligations?"',
#             key="rag_question",
#             label_visibility="collapsed",
#         )
#     with col_btn:
#         send = st.button("Send 🚀", use_container_width=True, key="rag_send")

#     # ── Example questions ─────────────────────────────────────
#     st.markdown(
#         "<p style='color:#999;font-size:.82rem;margin-top:8px;'>Try:</p>",
#         unsafe_allow_html=True,
#     )
#     examples = [
#         "What are NDA obligations?",
#         "Summarize incident response plan",
#         "What does SLA say about uptime?",
#         "HR leave policy details",
#     ]
#     ex_cols = st.columns(4)
#     for i, ex in enumerate(examples):
#         with ex_cols[i]:
#             if st.button(ex, key=f"rag_ex_{i}", use_container_width=True):
#                 question = ex
#                 send     = True

#     if send and question.strip():
#         with st.spinner("🔍 Searching knowledge base..."):
#             payload = {
#                 "question":   question,
#                 "session_id": st.session_state.rag_session_id,
#                 "use_refine": True,
#                 "top_k":      5,
#             }
#             payload.update(filters)
#             result = api_post("/rag/answer", payload)

#         if result and result.get("success"):
#             st.session_state.rag_chat_history.append(
#                 {"role": "user", "content": question}
#             )
#             st.session_state.rag_chat_history.append({
#                 "role":      "assistant",
#                 "content":   result["answer"],
#                 "citations": result.get("citations", []),
#             })
#             if result.get("refined_query") and result["refined_query"] != question:
#                 st.info(f"🔄 Refined: *{result['refined_query']}*")
#             st.rerun()

#     # ── Footer ────────────────────────────────────────────────
#     st.markdown("<hr class='divider'>", unsafe_allow_html=True)
#     fc1, fc2 = st.columns(2)
#     with fc1:
#         st.markdown(
#             f"<p style='color:#999;font-size:.8rem;'>Session: "
#             f"{st.session_state.rag_session_id}</p>",
#             unsafe_allow_html=True,
#         )
#     with fc2:
#         if st.button("🗑️ Clear Chat", key="rag_clear", use_container_width=True):
#             import uuid
#             st.session_state.rag_chat_history = []
#             st.session_state.rag_session_id   = str(uuid.uuid4())[:8]
#             st.rerun()


# # ============================================================
# # PAGE: RAG SEARCH INSPECTOR (MODERN UI)
# # ============================================================
# def page_rag_search():
#     # Custom CSS for modern UI
#     st.markdown("""
#         <style>
#         /* Modern gradient header */
#         .modern-header {
#             background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#             padding: 2rem;
#             border-radius: 1rem;
#             margin-bottom: 2rem;
#             text-align: center;
#             box-shadow: 0 10px 30px rgba(0,0,0,0.1);
#         }
#         .modern-header h1 {
#             color: white !important;
#             margin: 0 !important;
#             font-size: 2.5rem !important;
#             font-weight: 700 !important;
#         }
#         .modern-header p {
#             color: rgba(255,255,255,0.9) !important;
#             margin-top: 0.5rem !important;
#         }
        
#         /* Search card */
#         .search-card {
#             background: white;
#             padding: 1.5rem;
#             border-radius: 1rem;
#             box-shadow: 0 2px 10px rgba(0,0,0,0.05);
#             margin-bottom: 1.5rem;
#             border: 1px solid #e0e0e0;
#         }
        
#         /* Result cards */
#         .result-card {
#             background: white;
#             border-radius: 1rem;
#             padding: 1.25rem;
#             margin-bottom: 1rem;
#             border-left: 4px solid;
#             transition: all 0.3s ease;
#             box-shadow: 0 2px 8px rgba(0,0,0,0.05);
#         }
#         .result-card:hover {
#             transform: translateX(5px);
#             box-shadow: 0 4px 15px rgba(0,0,0,0.1);
#         }
        
#         /* Score pill */
#         .score-pill {
#             display: inline-block;
#             padding: 0.5rem 1rem;
#             border-radius: 2rem;
#             font-weight: 700;
#             font-size: 1.2rem;
#             text-align: center;
#             min-width: 80px;
#         }
        
#         /* Metadata tags */
#         .meta-tag {
#             display: inline-block;
#             padding: 0.25rem 0.75rem;
#             background: #f0f0f0;
#             border-radius: 1rem;
#             font-size: 0.75rem;
#             margin-right: 0.5rem;
#             margin-bottom: 0.5rem;
#         }
        
#         /* Refiner card */
#         .refiner-card {
#             background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
#             padding: 1.5rem;
#             border-radius: 1rem;
#             margin-top: 2rem;
#         }
        
#         /* Stat cards */
#         .stat-modern {
#             background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#             padding: 1rem;
#             border-radius: 1rem;
#             text-align: center;
#             color: white;
#             transition: transform 0.3s ease;
#         }
#         .stat-modern:hover {
#             transform: translateY(-5px);
#         }
#         .stat-number-modern {
#             font-size: 2rem;
#             font-weight: 700;
#         }
#         .stat-label-modern {
#             font-size: 0.85rem;
#             opacity: 0.9;
#         }
        
#         /* Progress bar for relevance */
#         .relevance-bar {
#             height: 6px;
#             border-radius: 3px;
#             background: #e0e0e0;
#             margin-top: 8px;
#             overflow: hidden;
#         }
#         .relevance-fill {
#             height: 100%;
#             border-radius: 3px;
#             transition: width 0.5s ease;
#         }
        
#         /* Animations */
#         @keyframes fadeInUp {
#             from {
#                 opacity: 0;
#                 transform: translateY(20px);
#             }
#             to {
#                 opacity: 1;
#                 transform: translateY(0);
#             }
#         }
#         .fade-in {
#             animation: fadeInUp 0.5s ease;
#         }
#         </style>
#     """, unsafe_allow_html=True)

#     # Modern header
#     st.markdown("""
#         <div class="modern-header">
#             <h1>🔍 RAG Search Inspector</h1>
#             <p>Intelligent document retrieval with visual relevance scoring</p>
#         </div>
#     """, unsafe_allow_html=True)

#     # Search section
#     st.markdown('<div class="search-card">', unsafe_allow_html=True)
    
#     col1, col2, col3 = st.columns([3, 1, 1])
#     with col1:
#         query = st.text_input(
#             "🔎 Search query",
#             placeholder="e.g., termination clause, service uptime requirements...",
#             key="insp_query",
#             label_visibility="collapsed"
#         )
#     with col2:
#         sel_dept = st.selectbox(
#             "🏢 Department", 
#             ["All Departments"] + DEPARTMENTS, 
#             key="insp_dept"
#         )
#     with col3:
#         top_k = st.slider("📊 Top K results", 1, 15, 5, key="insp_k")
    
#     search_clicked = st.button("🔍 Search Knowledge Base", use_container_width=True, key="insp_btn")
    
#     if search_clicked and query.strip():
#         payload = {"query": query, "top_k": top_k}
#         if sel_dept != "All Departments": 
#             payload["department"] = sel_dept

#         with st.spinner("🔎 Searching vector database..."):
#             result = api_post("/rag/retrieve", payload)

#         if result and result.get("success"):
#             chunks = result.get("chunks", [])
#             cached = result.get("cached", False)
            
#             # Results header
#             col_status1, col_status2 = st.columns([3, 1])
#             with col_status1:
#                 st.markdown(f"""
#                     <div style="margin: 1rem 0;">
#                         <span style="font-size: 1.2rem; font-weight: 600;">📄 Found {len(chunks)} relevant chunks</span>
#                         {"<span style='margin-left: 1rem; background: #4CAF50; color: white; padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.8rem;'>⚡ Cached Results</span>" if cached else ""}
#                     </div>
#                 """, unsafe_allow_html=True)
            
#             # Display results
#             for i, chunk in enumerate(chunks, 1):
#                 meta = chunk.get("metadata", {})
#                 score = chunk.get("score", 0)
                
#                 # Color based on relevance
#                 border_color = "#4CAF50" if score > 0.7 else "#FF9800" if score > 0.5 else "#f44336"
#                 score_color = "#4CAF50" if score > 0.7 else "#FF9800" if score > 0.5 else "#f44336"
                
#                 st.markdown(f"""
#                     <div class="result-card fade-in" style="border-left-color: {border_color};">
#                         <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
#                             <div>
#                                 <span style="font-weight: 700; font-size: 1.1rem; color: #1e3c72;">#{i}</span>
#                                 <span style="color: #666; margin-left: 0.5rem;">{chunk.get('citation', 'Untitled')}</span>
#                             </div>
#                             <div class="score-pill" style="background: {score_color}20; color: {score_color};">
#                                 {int(score*100)}%
#                             </div>
#                         </div>
#                         <div style="margin-bottom: 0.75rem;">
#                             <span class="meta-tag">🏛️ {meta.get('department', 'N/A')}</span>
#                             <span class="meta-tag">📄 {meta.get('doc_type', 'N/A')}</span>
#                             <span class="meta-tag">🔖 v{meta.get('version', 'N/A')}</span>
#                         </div>
#                         <div style="color: #444; line-height: 1.6; margin: 1rem 0;">
#                             {chunk.get('text', '')[:400]}{'...' if len(chunk.get('text', '')) > 400 else ''}
#                         </div>
#                         <div class="relevance-bar">
#                             <div class="relevance-fill" style="width: {score*100}%; background: {score_color};"></div>
#                         </div>
#                     </div>
#                 """, unsafe_allow_html=True)
                
#                 # Expandable full text option
#                 with st.expander(f"📖 View full text ({len(chunk.get('text', ''))} chars)"):
#                     st.text(chunk.get('text', ''))
    
#     st.markdown('</div>', unsafe_allow_html=True)

#     # Query Refiner Section
#     st.markdown("""
#         <div class="refiner-card">
#             <h2 style="color: #333; margin-bottom: 1rem;">✨ Smart Query Refiner</h2>
#             <p style="color: #666; margin-bottom: 1rem;">Transform vague queries into precise search terms</p>
#         </div>
#     """, unsafe_allow_html=True)
    
#     col_ref1, col_ref2 = st.columns([4, 1])
#     with col_ref1:
#         ref_query = st.text_input(
#             "Enter your query",
#             placeholder="e.g., what happens when contract ends, service uptime requirements...",
#             key="ref_q",
#             label_visibility="collapsed"
#         )
#     with col_ref2:
#         refine_clicked = st.button("✨ Refine Query", use_container_width=True, key="ref_btn")
    
#     if refine_clicked and ref_query.strip():
#         with st.spinner("🧠 Analyzing and refining query..."):
#             result = api_post("/rag/refine", {"query": ref_query, "context": ""})
#         if result and result.get("success"):
#             st.markdown(f"""
#                 <div style="background: white; padding: 1rem; border-radius: 0.5rem; margin-top: 1rem; border-left: 4px solid #667eea;">
#                     <span style="font-weight: 600;">🎯 Refined Query:</span><br>
#                     <span style="color: #333; font-size: 1.1rem;">{result['refined']}</span>
#                 </div>
#             """, unsafe_allow_html=True)
            
#             if result.get("keywords"):
#                 st.markdown("""
#                     <div style="margin-top: 1rem;">
#                         <span style="font-weight: 600;">🔑 Key Concepts:</span><br>
#                 """, unsafe_allow_html=True)
#                 keywords_html = "".join([f'<span class="meta-tag" style="background: #667eea20; color: #667eea;">{kw}</span>' for kw in result["keywords"]])
#                 st.markdown(keywords_html, unsafe_allow_html=True)
#                 st.markdown("</div>", unsafe_allow_html=True)
            
#             if result.get("suggestions"):
#                 st.markdown("""
#                     <div style="margin-top: 1rem;">
#                         <span style="font-weight: 600;">💡 Search Suggestions:</span>
#                         <ul style="margin-top: 0.5rem;">
#                 """, unsafe_allow_html=True)
#                 for s in result["suggestions"]:
#                     st.markdown(f"<li>{s}</li>", unsafe_allow_html=True)
#                 st.markdown("</ul></div>", unsafe_allow_html=True)

#     # Knowledge Base Stats
#     st.markdown("""
#         <div style="margin-top: 2rem;">
#             <h2 style="color: #333; margin-bottom: 1rem;">📊 Knowledge Base Insights</h2>
#         </div>
#     """, unsafe_allow_html=True)
    
#     if st.button("🔄 Refresh Statistics", use_container_width=True, key="rag_stats_btn"):
#         stats = api_get("/rag/stats")
#         if stats and stats.get("success"):
#             vs = stats["vector_store"]
#             redis = stats["redis"]
            
#             col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            
#             with col_s1:
#                 st.markdown(f"""
#                     <div class="stat-modern">
#                         <div class="stat-number-modern">{vs.get('total_chunks', 0):,}</div>
#                         <div class="stat-label-modern">Total Chunks</div>
#                     </div>
#                 """, unsafe_allow_html=True)
            
#             with col_s2:
#                 st.markdown(f"""
#                     <div class="stat-modern" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
#                         <div class="stat-number-modern">{len(vs.get('doc_types', []))}</div>
#                         <div class="stat-label-modern">Document Types</div>
#                     </div>
#                 """, unsafe_allow_html=True)
            
#             with col_s3:
#                 st.markdown(f"""
#                     <div class="stat-modern" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
#                         <div class="stat-number-modern">{len(vs.get('departments', []))}</div>
#                         <div class="stat-label-modern">Departments</div>
#                     </div>
#                 """, unsafe_allow_html=True)
            
#             with col_s4:
#                 st.markdown(f"""
#                     <div class="stat-modern" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
#                         <div class="stat-number-modern">{redis.get('total_keys', 0):,}</div>
#                         <div class="stat-label-modern">Redis Keys</div>
#                     </div>
#                 """, unsafe_allow_html=True)
            
#             # Additional stats visualization
#             st.markdown("---")
#             st.markdown("#### 📈 Distribution Overview")
            
#             # Create a simple bar chart for doc types
#             doc_types = vs.get('doc_types')

#             if doc_types:
#                 doc_types_data = {}

#                 # Case 1: If it's a dictionary (best case)
#                 if isinstance(doc_types, dict):
#                     doc_types_data = {
#                         dt: doc_types.get(dt, 0)
#                         for dt in list(doc_types.keys())[:5]
#                     }

#                 # Case 2: If it's a list (fallback)
#                 elif isinstance(doc_types, list):
#                     doc_types_data = {
#                         dt: 1  # default count (or you can change logic)
#                         for dt in doc_types[:5]
#                     }

#                 # Final check before plotting
#                 if doc_types_data:
#                     st.bar_chart(doc_types_data)
#                 else:
#                     st.info("No document type data available for visualization.")
# # ============================================================
# # PAGE: COMPARE DOCS
# # ============================================================
# def page_rag_compare():
#     st.markdown(
#         "<h1 class='main-header'>⚖️ Compare Documents</h1>",
#         unsafe_allow_html=True,
#     )
#     st.markdown(
#         "<p style='text-align:center;color:#666;'>Compare two document types "
#         "side by side on any topic</p>",
#         unsafe_allow_html=True,
#     )
#     st.markdown("<hr class='divider'>", unsafe_allow_html=True)

#     c1, c2, c3 = st.columns([3, 3, 4])
#     with c1:
#         doc_a = st.selectbox("Document A", ALL_DOC_TYPES, key="cmp_a")
#     with c2:
#         doc_b = st.selectbox(
#             "Document B", ALL_DOC_TYPES,
#             index=min(1, len(ALL_DOC_TYPES)-1),
#             key="cmp_b",
#         )
#     with c3:
#         cmp_query = st.text_input(
#             "What to compare",
#             placeholder="e.g. termination clauses, liability, payment terms",
#             key="cmp_q",
#             label_visibility="collapsed",
#         )

#     if (
#         st.button("⚖️ Compare", use_container_width=True, key="cmp_btn")
#         and cmp_query.strip()
#     ):
#         if doc_a == doc_b:
#             st.warning("Please select two different document types!")
#         else:
#             with st.spinner(f"Comparing {doc_a} vs {doc_b}..."):
#                 result = api_post("/rag/compare", {
#                     "query":      cmp_query,
#                     "doc_type_a": doc_a,
#                     "doc_type_b": doc_b,
#                     "session_id": st.session_state.get("rag_session_id", "default"),
#                 })

#             if result and result.get("success"):
#                 col_a, col_b = st.columns(2)
#                 with col_a:
#                     st.markdown(
#                         f"<div class='custom-card'>"
#                         f"<b style='color:#1e3c72;'>{doc_a}</b>",
#                         unsafe_allow_html=True,
#                     )
#                     for cit in result["doc_a"]["citations"]:
#                         st.markdown(
#                             f"<div class='q-block' style='background:#E8F5E9;"
#                             f"border-left-color:#4CAF50;font-size:.85rem;'>📄 {cit}</div>",
#                             unsafe_allow_html=True,
#                         )
#                     st.markdown("</div>", unsafe_allow_html=True)
#                 with col_b:
#                     st.markdown(
#                         f"<div class='custom-card' style='border-left-color:#764ba2;'>"
#                         f"<b style='color:#1e3c72;'>{doc_b}</b>",
#                         unsafe_allow_html=True,
#                     )
#                     for cit in result["doc_b"]["citations"]:
#                         st.markdown(
#                             f"<div class='q-block' style='background:#F3E5F5;"
#                             f"border-left-color:#7B1FA2;font-size:.85rem;'>📄 {cit}</div>",
#                             unsafe_allow_html=True,
#                         )
#                     st.markdown("</div>", unsafe_allow_html=True)

#                 st.markdown("<hr class='divider'>", unsafe_allow_html=True)
#                 st.markdown(
#                     "<h2 class='sub-header'>📋 Comparison Result</h2>",
#                     unsafe_allow_html=True,
#                 )
#                 st.markdown(result["comparison"])

#                 # Save to session
#                 if "rag_chat_history" not in st.session_state:
#                     st.session_state.rag_chat_history = []
#                 st.session_state.rag_chat_history.append({
#                     "role":    "user",
#                     "content": f"Compare {doc_a} vs {doc_b}: {cmp_query}",
#                 })
#                 st.session_state.rag_chat_history.append({
#                     "role":      "assistant",
#                     "content":   result["comparison"],
#                     "citations": (
#                         result["doc_a"]["citations"] +
#                         result["doc_b"]["citations"]
#                     ),
#                 })

# # ============================================================
# # PAGE: RAGAS EVALUATION
# # ============================================================
# def page_rag_eval():
#     st.markdown("<h1 class='main-header'>📊 RAGAS Evaluation</h1>", unsafe_allow_html=True)
#     st.markdown(
#         "<p style='text-align:center;color:#666;'>Evaluate RAG pipeline quality — "
#         "Faithfulness, Answer Relevancy, Context Precision, Context Recall</p>",
#         unsafe_allow_html=True,
#     )
#     st.markdown("<hr class='divider'>", unsafe_allow_html=True)
 
#     # ── Info boxes ────────────────────────────────────────────
#     c1, c2, c3, c4 = st.columns(4)
#     for col, metric, desc, color in [
#         (c1, "Faithfulness",      "Answer grounded in context?",    "#667eea"),
#         (c2, "Answer Relevancy",  "Answer relevant to question?",   "#764ba2"),
#         (c3, "Context Precision", "Retrieved chunks relevant?",     "#4facfe"),
#         (c4, "Context Recall",    "All relevant info retrieved?",   "#11998e"),
#     ]:
#         with col:
#             st.markdown(
#                 f"<div style='background:{color};color:white;padding:12px;border-radius:10px;"
#                 f"text-align:center;margin-bottom:8px;'>"
#                 f"<b style='font-size:.85rem;'>{metric}</b><br>"
#                 f"<span style='font-size:.75rem;opacity:.9;'>{desc}</span></div>",
#                 unsafe_allow_html=True,
#             )
 
#     st.markdown("<hr class='divider'>", unsafe_allow_html=True)
 
#     # ── Run Evaluation ────────────────────────────────────────
#     st.markdown("<h2 class='sub-header'>🚀 Run Evaluation</h2>", unsafe_allow_html=True)
 
#     col1, col2 = st.columns(2)
#     with col1:
#         top_k      = st.slider("Top K chunks", 1, 10, 5, key="eval_topk")
#         use_refine = st.checkbox("Use query refinement", value=True, key="eval_refine")
#     with col2:
#         st.markdown(
#             "<div class='info-box' style='padding:12px;font-size:.85rem;'>"
#             "📋 Default dataset: 5 questions covering NDA, SLA, HR Policy, "
#             "Data Breach, and Vendor Contracts.</div>",
#             unsafe_allow_html=True,
#         )
 
#     # Custom dataset
#     with st.expander("➕ Add Custom Questions (optional)"):
#         custom_q = st.text_area(
#             "One question per line (format: question | ground_truth)",
#             placeholder="What are NDA obligations? | Receiving party must protect confidential info.\nWhat is the SLA uptime? | 99.9% availability guaranteed.",
#             height=120,
#             key="eval_custom",
#         )
 
#     if st.button("🚀 Run RAGAS Evaluation", use_container_width=True, key="eval_run"):
#         dataset = None
#         if custom_q.strip():
#             dataset = []
#             for line in custom_q.strip().split("\n"):
#                 if "|" in line:
#                     parts = line.split("|", 1)
#                     dataset.append({
#                         "question":     parts[0].strip(),
#                         "ground_truth": parts[1].strip(),
#                     })
#                 elif line.strip():
#                     dataset.append({"question": line.strip(), "ground_truth": ""})
 
#         with st.spinner("🔍 Running evaluation... This may take 2-3 minutes."):
#             result = api_post("/rag/eval/run", {
#                 "top_k":        top_k,
#                 "use_refine":   use_refine,
#                 "save_results": True,
#                 "filters":      {},
#                 "dataset":      dataset or [],
#             })
 
#         if result and result.get("success"):
#             st.success(f"✅ {result['message']}")
#             st.info("⏳ Results will be available in 2-3 minutes. Click 'Load Latest Results' below.")
 
#     st.markdown("<hr class='divider'>", unsafe_allow_html=True)
 
#     # ── Results ───────────────────────────────────────────────
#     st.markdown("<h2 class='sub-header'>📈 Latest Results</h2>", unsafe_allow_html=True)
 
#     if st.button("🔄 Load Latest Results", use_container_width=True, key="eval_load"):
#         result = api_get("/rag/eval/results")
#         if result and result.get("success") and result.get("results"):
#             data   = result["results"]
#             scores = data.get("scores", {})
 
#             # Score cards
#             overall = scores.get("overall", 0)
#             color   = "#4CAF50" if overall > 0.7 else "#FF9800" if overall > 0.5 else "#f44336"
 
#             st.markdown(
#                 f"<div style='background:{color};padding:16px;border-radius:12px;"
#                 f"text-align:center;color:white;margin:12px 0;'>"
#                 f"<div style='font-size:2rem;font-weight:700;'>{overall:.1%}</div>"
#                 f"<div style='font-size:.85rem;opacity:.9;'>Overall Score</div></div>",
#                 unsafe_allow_html=True,
#             )
 
#             mc1, mc2, mc3, mc4 = st.columns(4, gap="medium")
#             for col, key, label in [
#                 (mc1, "faithfulness",      "Faithfulness"),
#                 (mc2, "answer_relevancy",  "Answer Relevancy"),
#                 (mc3, "context_precision", "Context Precision"),
#                 (mc4, "context_recall",    "Context Recall"),
#             ]:
#                 with col:
#                     val   = scores.get(key, 0)
#                     clr   = "#4CAF50" if val > 0.7 else "#FF9800" if val > 0.5 else "#f44336"
#                     st.markdown(
#                         f"<div class='metric-box' style='background:linear-gradient(135deg,{clr},{clr}cc);'>"
#                         f"<div class='metric-number'>{val:.1%}</div>"
#                         f"<div class='metric-label'>{label}</div></div>",
#                         unsafe_allow_html=True,
#                     )
 
#             # Per-question results
#             st.markdown("<hr class='divider'>", unsafe_allow_html=True)
#             st.markdown("<h2 class='sub-header'>📋 Per-Question Results</h2>", unsafe_allow_html=True)
 
#             for i, item in enumerate(data.get("results", []), 1):
#                 with st.expander(f"Q{i}: {item['question'][:80]}..."):
#                     st.markdown(f"**Question:** {item['question']}")
#                     st.markdown(f"**Answer:** {item.get('answer', 'N/A')[:500]}")
#                     if item.get("citations"):
#                         st.markdown("**Citations:**")
#                         for cit in item["citations"]:
#                             st.markdown(
#                                 f"<div class='q-block' style='background:#E8F5E9;"
#                                 f"border-left-color:#4CAF50;font-size:.85rem;'>📄 {cit}</div>",
#                                 unsafe_allow_html=True,
#                             )
#                     if item.get("ground_truth"):
#                         st.markdown(f"**Ground Truth:** {item['ground_truth']}")
#                     st.markdown(
#                         f"<span style='color:#666;font-size:.8rem;'>"
#                         f"Chunks used: {item.get('chunks_used', 0)} | "
#                         f"Refined query: {item.get('refined_query', 'N/A')}</span>",
#                         unsafe_allow_html=True,
#                     )
 
#             # Config used
#             with st.expander("⚙️ Evaluation Config"):
#                 st.json(data.get("config", {}))
#                 st.markdown(f"**Timestamp:** {data.get('timestamp', 'N/A')}")
#                 st.markdown(f"**Dataset size:** {data.get('dataset_size', 0)}")
 
#         elif result and result.get("success") and not result.get("results"):
#             st.info("No results yet — run evaluation first!")
 
#     # ── History ───────────────────────────────────────────────
#     st.markdown("<hr class='divider'>", unsafe_allow_html=True)
#     st.markdown("<h2 class='sub-header'>📜 Evaluation History</h2>", unsafe_allow_html=True)
 
#     if st.button("📜 Load History", use_container_width=True, key="eval_history"):
#         result = api_get("/rag/eval/history")
#         if result and result.get("history"):
#             history = result["history"]
#             st.markdown(f"**{len(history)} evaluation runs found**")
 
#             import pandas as pd
#             rows = []
#             for h in history:
#                 scores = h.get("scores", {})
#                 rows.append({
#                     "Timestamp":         h.get("timestamp", "")[:16],
#                     "Overall":           f"{scores.get('overall', 0):.1%}",
#                     "Faithfulness":      f"{scores.get('faithfulness', 0):.1%}",
#                     "Answer Relevancy":  f"{scores.get('answer_relevancy', 0):.1%}",
#                     "Context Precision": f"{scores.get('context_precision', 0):.1%}",
#                     "Context Recall":    f"{scores.get('context_recall', 0):.1%}",
#                     "Questions":         h.get("dataset_size", 0),
#                     "File":              h.get("filename", ""),
#                 })
#             st.dataframe(pd.DataFrame(rows), use_container_width=True)
#         else:
#             st.info("No evaluation history found.")


# ============================================================
# STEP 1 — Add these constants in document_app.py
# Place right after:  ALL_DOC_TYPES = sorted({...})
# ============================================================

ALL_INDUSTRIES = ["SaaS",]

ALL_VERSIONS = ["v1", "v2", "v3", "v4", "v5"]


# ============================================================
# STEP 2 — Replace your entire page_rag_chat() with this
# ============================================================

def page_rag_chat():
    import uuid

    if "rag_session_id" not in st.session_state:
        st.session_state.rag_session_id = str(uuid.uuid4())[:8]

    # ── Global CSS ───────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    /* ── Header ── */
    .rag-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 36px 28px 30px;
        text-align: center;
        margin-bottom: 28px;
        box-shadow: 0 8px 32px rgba(102,126,234,0.35);
        position: relative;
        overflow: hidden;
    }
    .rag-header::before {
        content: '';
        position: absolute;
        top: -40px; right: -40px;
        width: 160px; height: 160px;
        background: rgba(255,255,255,0.07);
        border-radius: 50%;
    }
    .rag-header h1 { color: white; margin: 0 0 8px; font-size: 2.2rem; font-weight: 700; }
    .rag-header p  { color: rgba(255,255,255,0.88); margin: 0; font-size: 1rem; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: #f0f2ff;
        padding: 6px;
        border-radius: 14px;
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 14px;
        font-weight: 500;
        padding: 10px 22px;
        border-radius: 10px;
        color: #667eea;
        border: none !important;
        background: transparent;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(102,126,234,0.4);
    }

    /* ── Filter bar ── */
    .filter-bar {
        background: linear-gradient(135deg, #f8f9ff, #f0f2ff);
        border: 1.5px solid #e0e4ff;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 20px;
    }
    .filter-title {
        font-size: 12px;
        font-weight: 600;
        color: #667eea;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 10px;
    }

    /* ── Chat bubbles ── */
    .chat-wrap { display: flex; flex-direction: column; gap: 14px; margin-bottom: 20px; }

    .bubble-user {
        align-self: flex-end;
        max-width: 72%;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        font-size: 14px;
        line-height: 1.6;
        box-shadow: 0 4px 14px rgba(102,126,234,0.3);
    }

    .bubble-ai {
        align-self: flex-start;
        max-width: 78%;
        background: white;
        color: #2d2d2d;
        padding: 14px 18px;
        border-radius: 4px 18px 18px 18px;
        font-size: 14px;
        line-height: 1.7;
        border: 1.5px solid #e8eaff;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    }

    .bubble-label {
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 5px;
        opacity: 0.75;
    }

    /* ── Citation badges ── */
    .cite-strip { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }
    .cite-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: linear-gradient(135deg, #eef0ff, #f5f0ff);
        border: 1px solid #d0d4ff;
        color: #534AB7;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 500;
        padding: 4px 10px;
        cursor: default;
    }
    .cite-score {
        background: #667eea;
        color: white;
        border-radius: 10px;
        font-size: 10px;
        padding: 1px 6px;
        font-weight: 600;
    }

    /* ── Rationale box ── */
    .rationale-box {
        margin-top: 10px;
        background: #fffbf0;
        border-left: 3px solid #f59e0b;
        border-radius: 0 8px 8px 0;
        padding: 8px 12px;
        font-size: 12px;
        color: #78350f;
    }

    /* ── Empty state ── */
    .empty-state {
        text-align: center;
        padding: 48px 24px;
        color: #9ca3af;
    }
    .empty-state .icon { font-size: 3rem; margin-bottom: 12px; }
    .empty-state h3 { color: #6b7280; margin-bottom: 8px; font-size: 1.1rem; }
    .empty-state p  { font-size: 0.88rem; line-height: 1.6; }

    /* ── Example chips ── */
    .example-chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
    .example-chip {
        background: white;
        border: 1.5px solid #e0e4ff;
        color: #667eea;
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 12px;
        cursor: pointer;
        font-weight: 500;
    }
    .example-chip:hover { background: #f0f2ff; }

    /* ── Chunk card ── */
    .chunk-card {
        background: white;
        border: 1.5px solid #e8eaff;
        border-radius: 14px;
        padding: 16px 18px;
        margin-bottom: 12px;
        transition: border-color 0.2s;
    }
    .chunk-card:hover { border-color: #667eea; }
    .chunk-rank {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 26px; height: 26px;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border-radius: 50%;
        font-size: 12px;
        font-weight: 700;
        margin-right: 8px;
        flex-shrink: 0;
    }
    .chunk-title { font-weight: 600; color: #1e3c72; font-size: 14px; }
    .chunk-section { color: #667eea; font-size: 12px; }
    .chunk-pill {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 500;
        margin-right: 4px;
    }
    .pill-ind  { background: #e8f5e9; color: #2e7d32; }
    .pill-type { background: #e8eaff; color: #3730a3; }
    .pill-ver  { background: #fff3e0; color: #e65100; }
    .chunk-text-preview {
        font-size: 13px;
        color: #4b5563;
        line-height: 1.6;
        margin-top: 10px;
        border-top: 1px solid #f0f0f0;
        padding-top: 10px;
    }
    .score-bar-wrap { margin-top: 10px; }
    .score-bar-bg { background: #f0f0f0; border-radius: 4px; height: 6px; overflow: hidden; }
    .score-bar-fill { height: 100%; border-radius: 4px; }

    /* ── Compare card ── */
    .compare-card {
        background: white;
        border: 1.5px solid #e8eaff;
        border-radius: 16px;
        padding: 20px;
        height: 100%;
    }
    .compare-card-header {
        font-weight: 600;
        font-size: 15px;
        color: #1e3c72;
        margin-bottom: 12px;
        padding-bottom: 10px;
        border-bottom: 2px solid #f0f2ff;
    }

    /* ── Metric cards ── */
    .eval-metric {
        background: white;
        border: 1.5px solid #e8eaff;
        border-radius: 14px;
        padding: 18px;
        text-align: center;
    }
    .eval-metric-num {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .eval-metric-label {
        font-size: 11px;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 4px;
    }

    /* ── Session badge ── */
    .session-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #f0f2ff;
        border: 1px solid #d0d4ff;
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 11px;
        color: #667eea;
        font-weight: 500;
    }

    /* ── Input area ── */
    .stChatInput > div {
        border: 2px solid #e0e4ff !important;
        border-radius: 14px !important;
        background: white !important;
    }
    .stChatInput > div:focus-within {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102,126,234,0.15) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ──────────────────────────────────────────────────────────────
    st.markdown("""
        <div class="rag-header">
            <h1>🤖 RAG Assistant</h1>
            <p>Notion-powered knowledge base &nbsp;·&nbsp; Chat &nbsp;·&nbsp; Search &nbsp;·&nbsp; Compare &nbsp;·&nbsp; Evaluate</p>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["💬  Chat", "🔍  Search & Inspect", "📊  Evaluation"])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — CHAT
    # ════════════════════════════════════════════════════════════════════════
    with tab1:
        if "rag_chat_history" not in st.session_state:
            st.session_state.rag_chat_history = []

        # ── Filter bar ──────────────────────────────────────────────────────
        st.markdown('<div class="filter-bar"><div class="filter-title">⚙️ Retrieval Filters</div>', unsafe_allow_html=True)
        fc1, fc2, fc3, fc4 = st.columns([2, 2, 1, 1])
        with fc1:
            filter_industry = st.selectbox("Industry", ["All"] + ALL_INDUSTRIES, key="chat_filter_industry", label_visibility="collapsed")
        with fc2:
            filter_doc_type = st.selectbox("Doc Type", ["All"] + ALL_DOC_TYPES, key="chat_filter_doc_type", label_visibility="collapsed")
        with fc3:
            filter_version = st.selectbox("Version", ["All"] + ALL_VERSIONS, key="chat_filter_version", label_visibility="collapsed")
        with fc4:
            top_k = st.number_input("Top-K", 1, 10, 5, key="chat_top_k", label_visibility="collapsed")
        uc1, uc2 = st.columns([2, 5])
        with uc1:
            use_refine = st.toggle("✨ Use Refine", value=True, key="chat_use_refine")
        st.markdown('</div>', unsafe_allow_html=True)

        metadata_filter = {}
        if filter_industry != "All": metadata_filter["industry"]  = filter_industry
        if filter_doc_type != "All": metadata_filter["doc_type"]  = filter_doc_type
        if filter_version  != "All": metadata_filter["version"]   = filter_version

        # ── Example questions ────────────────────────────────────────────────
        if not st.session_state.rag_chat_history:
            st.markdown("""
            <div class="empty-state">
                <div class="icon">🧠</div>
                <h3>Ask anything about your documents</h3>
                <p>Your Notion knowledge base is ready.<br>Try one of these examples or type your own question below.</p>
            </div>
            """, unsafe_allow_html=True)

            examples = [
                "📋 Create a compliant incident response summary",
                "⚖️ Compare SOW vs MSA clauses",
                "🔒 What are NDA confidentiality obligations?",
                "📈 Summarise the SLA uptime requirements",
                "👥 What does the HR leave policy say?",
                "🛡️ What's in the Data Processing Agreement?",
            ]
            cols = st.columns(3)
            for i, ex in enumerate(examples):
                with cols[i % 3]:
                    if st.button(ex, key=f"ex_{i}", use_container_width=True):
                        st.session_state._prefill_question = ex.split(" ", 1)[1]
                        st.rerun()

        # ── Chat history ─────────────────────────────────────────────────────
        for msg in st.session_state.rag_chat_history:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])
                    citations = msg.get("citations", [])
                    if citations:
                        badges_html = '<div class="cite-strip">'
                        for cite in citations:
                            doc   = cite.get("doc_title", "Doc")
                            sec   = cite.get("section", "")
                            score = cite.get("score", 0)
                            label = f"📄 {doc}" + (f" › {sec}" if sec else "")
                            pct   = f"{score:.0%}" if isinstance(score, float) else str(score)
                            badges_html += f'<span class="cite-badge">{label}<span class="cite-score">{pct}</span></span>'
                        badges_html += '</div>'
                        st.markdown(badges_html, unsafe_allow_html=True)
                    rationale = msg.get("rationale", "")
                    if rationale:
                        st.markdown(
                            f'<div class="rationale-box">🧠 <b>Rationale:</b> {rationale}</div>',
                            unsafe_allow_html=True
                        )

        # ── Input ─────────────────────────────────────────────────────────────
        prefill = st.session_state.pop("_prefill_question", "")
        question = st.chat_input(prefill or "Ask anything about your documents…")

        if question:
            st.session_state.rag_chat_history.append({"role": "user", "content": question})
            with st.spinner("🔍 Searching knowledge base…"):
                result = api_post("/rag/answer", {
                    "question":        question,
                    "session_id":      st.session_state.rag_session_id,
                    "top_k":           top_k,
                    "use_refine":      use_refine,
                    "metadata_filter": metadata_filter,
                })
            if result and result.get("success"):
                st.session_state.rag_chat_history.append({
                    "role":      "assistant",
                    "content":   result.get("answer", ""),
                    "citations": result.get("citations", []),
                    "rationale": result.get("rationale", ""),
                })
            else:
                st.session_state.rag_chat_history.append({
                    "role":    "assistant",
                    "content": "⚠️ I couldn't find an answer. The document may not be ingested yet, or the backend is offline.",
                })
            st.rerun()

        # ── Footer row ────────────────────────────────────────────────────────
        if st.session_state.rag_chat_history:
            fc1, fc2 = st.columns([1, 1])
            with fc1:
                st.markdown(
                    f'<span class="session-badge">🔑 Session: {st.session_state.rag_session_id}</span>',
                    unsafe_allow_html=True
                )
            with fc2:
                if st.button("🗑️ Clear chat", key="clear_chat", use_container_width=True):
                    st.session_state.rag_chat_history = []
                    st.session_state.rag_session_id   = str(uuid.uuid4())[:8]
                    st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — SEARCH & RETRIEVAL INSPECTOR
    # ════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
                <div style="width:40px;height:40px;background:linear-gradient(135deg,#667eea,#764ba2);
                            border-radius:10px;display:flex;align-items:center;justify-content:center;
                            font-size:18px;">🔍</div>
                <div>
                    <div style="font-weight:700;font-size:1.1rem;color:#1e3c72;">Smart Search & Retrieval Inspector</div>
                    <div style="font-size:12px;color:#9ca3af;">Inspect retrieved chunks, scores, and metadata in real time</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Search box
        query = st.text_input(
            "Query",
            placeholder="e.g. termination clause, service uptime, confidentiality obligations…",
            key="search_query",
            label_visibility="collapsed"
        )

        sc1, sc2, sc3, sc4 = st.columns([2, 2, 1, 1])
        with sc1:
            s_industry = st.selectbox("Industry", ["All"] + ALL_INDUSTRIES, key="search_ind", label_visibility="collapsed")
        with sc2:
            s_doc_type = st.selectbox("Doc Type", ["All"] + ALL_DOC_TYPES, key="search_dt", label_visibility="collapsed")
        with sc3:
            s_top_k = st.number_input("Top-K", 1, 20, 5, key="search_k", label_visibility="collapsed")
        with sc4:
            s_version = st.selectbox("Version", ["All"] + ALL_VERSIONS, key="search_ver", label_visibility="collapsed")

        btn1, btn2 = st.columns(2)
        with btn1:
            do_search = st.button("🔍 Search Knowledge Base", use_container_width=True)
        with btn2:
            do_refine = st.button("✨ AI Query Refiner", use_container_width=True)

        # Refine
        if do_refine and query:
            with st.spinner("🧠 Refining query…"):
                ref = api_post("/rag/refine_query", {"query": query})
            if ref and ref.get("success"):
                refined = ref.get("refined_query", query)
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#f0f2ff,#f5f0ff);border:1.5px solid #d0d4ff;'
                    f'border-radius:12px;padding:12px 16px;margin:10px 0;">'
                    f'<span style="font-size:11px;font-weight:600;color:#667eea;text-transform:uppercase;letter-spacing:.08em;">✨ Refined Query</span><br>'
                    f'<span style="font-size:15px;color:#1e3c72;font-weight:500;">{refined}</span></div>',
                    unsafe_allow_html=True
                )
                st.session_state["refined_query"] = refined

        effective_query = st.session_state.get("refined_query", query)

        # Execute search
        if do_search and effective_query:
            s_filter = {}
            if s_industry != "All": s_filter["industry"] = s_industry
            if s_doc_type != "All": s_filter["doc_type"] = s_doc_type
            if s_version  != "All": s_filter["version"]  = s_version

            with st.spinner("🔎 Searching vector database…"):
                res = api_post("/rag/retrieve", {
                    "query":           effective_query,
                    "top_k":           s_top_k,
                    "metadata_filter": s_filter,
                })
            if res and res.get("success"):
                st.session_state["search_results"] = res.get("chunks", [])
                st.session_state.pop("refined_query", None)
            else:
                st.warning("⚠️ No results returned. Check the backend connection.")

        # Results
        chunks = st.session_state.get("search_results", [])
        if chunks:
            cached = st.session_state.get("search_cached", False)
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin:16px 0 8px;">'
                f'<span style="font-weight:700;color:#1e3c72;">{len(chunks)} chunks retrieved</span>'
                + (f'<span style="background:#e8f5e9;color:#2e7d32;border-radius:20px;'
                   f'padding:2px 10px;font-size:11px;font-weight:600;">⚡ Cached</span>' if cached else '')
                + '</div>',
                unsafe_allow_html=True
            )

            for i, chunk in enumerate(chunks):
                score     = chunk.get("score", 0)
                doc_title = chunk.get("doc_title", chunk.get("citation", f"Document {i+1}"))
                section   = chunk.get("section", "")
                text      = chunk.get("text", "")
                meta      = chunk.get("metadata", {})
                ind       = meta.get("industry", "—")
                dt        = meta.get("doc_type", "—")
                ver       = meta.get("version", "—")
                page_id   = chunk.get("page_id", "")
                block     = chunk.get("block_range", "")

                # Score color
                if score > 0.75:   bar_color = "#4CAF50"
                elif score > 0.5:  bar_color = "#FF9800"
                else:              bar_color = "#f44336"

                st.markdown(f"""
                <div class="chunk-card">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                        <div style="display:flex;align-items:center;">
                            <span class="chunk-rank">{i+1}</span>
                            <div>
                                <div class="chunk-title">{doc_title}</div>
                                {f'<div class="chunk-section">› {section}</div>' if section else ''}
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:1.3rem;font-weight:700;color:{bar_color};">{int(score*100)}%</div>
                            <div style="font-size:10px;color:#9ca3af;">relevance</div>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <span class="chunk-pill pill-ind">🏭 {ind}</span>
                        <span class="chunk-pill pill-type">📁 {dt}</span>
                        <span class="chunk-pill pill-ver">🔖 {ver}</span>
                        {f'<span class="chunk-pill" style="background:#f5f5f5;color:#666;">🔗 {page_id[:12]}…</span>' if page_id else ''}
                    </div>
                    <div class="score-bar-wrap">
                        <div class="score-bar-bg">
                            <div class="score-bar-fill" style="width:{score*100:.1f}%;background:{bar_color};"></div>
                        </div>
                    </div>
                    <div class="chunk-text-preview">{text[:350]}{'…' if len(text) > 350 else ''}</div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander(f"📖 Full text ({len(text):,} chars)"):
                    st.text(text)
                    if page_id:
                        st.caption(f"page_id: `{page_id}`   block_range: `{block}`")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 — EVALUATION
    # ════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
                <div style="width:40px;height:40px;background:linear-gradient(135deg,#667eea,#764ba2);
                            border-radius:10px;display:flex;align-items:center;justify-content:center;
                            font-size:18px;">📊</div>
                <div>
                    <div style="font-weight:700;font-size:1.1rem;color:#1e3c72;">Evaluation Dashboard</div>
                    <div style="font-size:12px;color:#9ca3af;">Compare documents and measure RAG pipeline quality with RAGAS</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        sub1, sub2 = st.tabs(["⚖️  Compare Docs", "📈  RAGAS Eval"])

        # ── SUB-TAB: Compare ─────────────────────────────────────────────────
        with sub1:
            st.markdown("""
            <div style="background:linear-gradient(135deg,#f8f9ff,#f0f2ff);border:1.5px solid #e0e4ff;
                        border-radius:14px;padding:16px 20px;margin-bottom:20px;">
                <div style="font-weight:600;color:#1e3c72;margin-bottom:4px;">⚖️ Side-by-side Document Comparison</div>
                <div style="font-size:12px;color:#9ca3af;">Select two document types and a question — see how RAG answers differ across them.</div>
            </div>
            """, unsafe_allow_html=True)

            cc1, cc2 = st.columns(2)
            with cc1:
                doc_a = st.selectbox("📄 Document A", ALL_DOC_TYPES, key="cmp_doc_a")
            with cc2:
                doc_b = st.selectbox("📄 Document B", ALL_DOC_TYPES,
                                     index=min(1, len(ALL_DOC_TYPES)-1), key="cmp_doc_b")

            cmp_query = st.text_input(
                "Comparison question",
                value="What are the key obligations and limitations?",
                key="cmp_query",
                placeholder="e.g. What are the termination rights?"
            )

            if st.button("⚖️ Run Comparison", use_container_width=True, key="btn_compare"):
                if doc_a == doc_b:
                    st.warning("⚠️ Please select two different document types.")
                else:
                    with st.spinner(f"Comparing {doc_a} vs {doc_b}…"):
                        res = api_post("/rag/compare", {
                            "doc_type_a": doc_a,
                            "doc_type_b": doc_b,
                            "query":      cmp_query,
                        })
                    if res and res.get("success"):
                        ca1, ca2 = st.columns(2)
                        with ca1:
                            st.markdown(f"""
                            <div class="compare-card">
                                <div class="compare-card-header"
                                     style="border-color:#667eea;">📄 {doc_a}</div>
                            """, unsafe_allow_html=True)
                            st.markdown(res.get("answer_a", "—"))
                            for cite in res.get("citations_a", []):
                                st.caption(f"› {cite.get('doc_title','—')} · {cite.get('section','')}")
                            st.markdown('</div>', unsafe_allow_html=True)
                        with ca2:
                            st.markdown(f"""
                            <div class="compare-card">
                                <div class="compare-card-header"
                                     style="border-color:#764ba2;">📄 {doc_b}</div>
                            """, unsafe_allow_html=True)
                            st.markdown(res.get("answer_b", "—"))
                            for cite in res.get("citations_b", []):
                                st.caption(f"› {cite.get('doc_title','—')} · {cite.get('section','')}")
                            st.markdown('</div>', unsafe_allow_html=True)

                        st.markdown("""
                        <div style="background:linear-gradient(135deg,#f8f9ff,#f0f2ff);
                                    border:1.5px solid #e0e4ff;border-radius:14px;
                                    padding:16px 20px;margin-top:16px;">
                            <div style="font-weight:600;color:#1e3c72;margin-bottom:10px;">
                                🔍 AI Comparison Summary
                            </div>
                        """, unsafe_allow_html=True)
                        st.markdown(res.get("comparison", "—"))
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.error("❌ Comparison failed. Check the backend connection.")

        # ── SUB-TAB: RAGAS Eval ──────────────────────────────────────────────
        with sub2:
            # Info cards
            m1, m2, m3, m4 = st.columns(4)
            for col, icon, label, desc, color in [
                (m1, "🎯", "Faithfulness",      "Answer grounded?",       "#667eea"),
                (m2, "💡", "Answer Relevancy",  "Relevant to question?",  "#764ba2"),
                (m3, "📌", "Context Precision",  "Chunks are on-point?",   "#4facfe"),
                (m4, "🔁", "Context Recall",    "All info retrieved?",    "#11998e"),
            ]:
                with col:
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,{color}18,{color}08);
                                border:1.5px solid {color}33;border-radius:14px;
                                padding:14px;text-align:center;margin-bottom:16px;">
                        <div style="font-size:1.6rem;">{icon}</div>
                        <div style="font-weight:600;font-size:13px;color:#1e3c72;margin:4px 0;">{label}</div>
                        <div style="font-size:11px;color:#9ca3af;">{desc}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # Config
            st.markdown("""
            <div style="background:linear-gradient(135deg,#f8f9ff,#f0f2ff);border:1.5px solid #e0e4ff;
                        border-radius:14px;padding:16px 20px;margin-bottom:16px;">
                <div style="font-weight:600;color:#1e3c72;margin-bottom:12px;">⚙️ Evaluation Config</div>
            """, unsafe_allow_html=True)

            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                eval_top_k = st.number_input("Top-K", 1, 20, 5, key="eval_k")
            with ec2:
                eval_strategy = st.selectbox("Strategy", ["dense", "hybrid", "rerank"], key="eval_strat")
            with ec3:
                eval_chunk_sz = st.selectbox("Chunk size", [256, 512, 1024], index=1, key="eval_chunk")
            st.markdown('</div>', unsafe_allow_html=True)

            eb1, eb2 = st.columns(2)
            with eb1:
                if st.button("▶️ Run Evaluation", use_container_width=True, key="btn_eval"):
                    with st.spinner("🔬 Running RAGAS evaluation — this may take 1–2 minutes…"):
                        api_post("/rag/eval/run", {
                            "top_k":      eval_top_k,
                            "strategy":   eval_strategy,
                            "chunk_size": eval_chunk_sz,
                        })
                    st.success("✅ Evaluation queued! Click 'Load Results' to view scores.")
            with eb2:
                if st.button("📥 Load Results", use_container_width=True, key="btn_eval_load"):
                    with st.spinner("Loading results…"):
                        res = api_get("/rag/eval/results")
                    if res and res.get("results"):
                        results = res["results"]
                        faith = results.get("faithfulness", 0)
                        relev = results.get("answer_relevancy", 0)
                        recall= results.get("context_recall", 0)
                        prec  = results.get("context_precision", 0)
                        overall = (faith + relev + recall + prec) / 4

                        # Overall bar
                        ov_color = "#4CAF50" if overall > 0.7 else "#FF9800" if overall > 0.5 else "#f44336"
                        st.markdown(f"""
                        <div style="background:linear-gradient(135deg,{ov_color},{ov_color}cc);
                                    border-radius:14px;padding:16px;text-align:center;margin:12px 0;color:white;">
                            <div style="font-size:2.2rem;font-weight:700;">{overall:.1%}</div>
                            <div style="font-size:12px;opacity:.9;text-transform:uppercase;letter-spacing:.1em;">Overall Score</div>
                        </div>
                        """, unsafe_allow_html=True)

                        # Individual metrics
                        rm1, rm2, rm3, rm4 = st.columns(4)
                        for col, val, lbl in [
                            (rm1, faith,  "Faithfulness"),
                            (rm2, relev,  "Ans. Relevancy"),
                            (rm3, recall, "Context Recall"),
                            (rm4, prec,   "Ctx. Precision"),
                        ]:
                            with col:
                                clr = "#4CAF50" if val > 0.7 else "#FF9800" if val > 0.5 else "#f44336"
                                st.markdown(f"""
                                <div class="eval-metric">
                                    <div class="eval-metric-num" style="background:linear-gradient(135deg,{clr},{clr}aa);
                                         -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                                         {val:.1%}</div>
                                    <div class="eval-metric-label">{lbl}</div>
                                </div>
                                """, unsafe_allow_html=True)

                        st.divider()
                        cfg = results.get("config", {})
                        if cfg:
                            with st.expander("🔧 Config used"):
                                st.json(cfg)
                        rows = results.get("rows", [])
                        if rows:
                            with st.expander("📋 Per-question breakdown"):
                                st.dataframe(rows, use_container_width=True)
                    else:
                        st.info("ℹ️ No results yet — run an evaluation first.")
# ============================================================
# MAIN
# ============================================================


st.set_page_config(
    page_title='DocForgeHub',
    page_icon='📄',
    layout='wide',
    initial_sidebar_state='expanded',
)

def main():
    logger.info("Starting Streamlit app - DocForgeHub")
    load_css()
    init_session()
    render_sidebar()
    page = st.session_state.page
    logger.debug(f"Current page: {page}")
    
    if   page == "Home":           page_home()
    elif page == "Generate":       page_generate()
    elif page == "Library":        page_library()
    elif page == "Templates":      page_templates()
    elif page == "Questionnaires": page_questionnaires()
    elif page == "Notion":         page_notion()
    elif page == "Stats":          page_stats()
    elif page == "AI Assistant":   page_rag_chat()
    # elif page == "RAG Search":     page_rag_search()
    # elif page == "Compare Docs":   page_rag_compare()
    # elif page == "RAG Eval": page_rag_eval()
    else:
        logger.warning(f"Unknown page requested: {page}")
        st.error(f"Unknown page: {page}")
        st.session_state.page = "Home"
        st.rerun()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Streamlit app started")
    logger.info("=" * 60)
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error in Streamlit app: {str(e)}", exc_info=True)
        raise


# # ============================================================
# # PAGE: LIBRARY
# # ============================================================
# 
@st.dialog("🗑️ Delete Document")
def confirm_delete_dialog(doc_id, doc_type):
    """GitHub-style centered delete confirmation dialog."""
    st.markdown(f"""
    <div style="text-align:center; padding:10px 0;">
        <div style="font-size:3rem;">🗑️</div>
        <h3 style="color:#24292f; margin:8px 0;">Delete this document?</h3>
        <p style="color:#57606a; font-size:0.9rem;">
            This action <strong>cannot be undone</strong>.<br>
            This will permanently delete this document.
        </p>
    </div>
    <div style="
        background:#fff8f0;
        border:1px solid #f5a623;
        border-radius:8px;
        padding:12px 16px;
        margin:12px 0;
        font-size:0.85rem;
        color:#633d00;
    ">
        To confirm, type <code style="
            background:#f0f0f0;
            padding:2px 6px;
            border-radius:4px;
            font-weight:700;
            color:#d73a49;
        ">{doc_type}</code> in the box below
    </div>
    """, unsafe_allow_html=True)

    confirm_input = st.text_input(
        "",
        placeholder=f"Type: {doc_type}",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns(2)
    with col1:
        delete_disabled = confirm_input.strip() != doc_type.strip()
        if st.button(
            "🗑️ Delete this document",
            use_container_width=True,
            type="primary",
            disabled=delete_disabled,
        ):
            st.session_state[f"do_delete_{doc_id}"] = True
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

def page_library():
    pass


# # # ============================================================
# # # PAGE: LIBRARY
# # # ============================================================
# # 
# @st.dialog("🗑️ Delete Document")
# def confirm_delete_dialog(doc_id, doc_type):
#     """GitHub-style centered delete confirmation dialog."""
#     st.markdown(f"""
#     <div style="text-align:center; padding:10px 0;">
#         <div style="font-size:3rem;">🗑️</div>
#         <h3 style="color:#24292f; margin:8px 0;">Delete this document?</h3>
#         <p style="color:#57606a; font-size:0.9rem;">
#             This action <strong>cannot be undone</strong>.<br>
#             This will permanently delete this document.
#         </p>
#     </div>
#     <div style="
#         background:#fff8f0;
#         border:1px solid #f5a623;
#         border-radius:8px;
#         padding:12px 16px;
#         margin:12px 0;
#         font-size:0.85rem;
#         color:#633d00;
#     ">
#         To confirm, type <code style="
#             background:#f0f0f0;
#             padding:2px 6px;
#             border-radius:4px;
#             font-weight:700;
#             color:#d73a49;
#         ">{doc_type}</code> in the box below
#     </div>
#     """, unsafe_allow_html=True)

#     confirm_input = st.text_input(
#         "",
#         placeholder=f"Type: {doc_type}",
#         label_visibility="collapsed",
#     )

#     col1, col2 = st.columns(2)
#     with col1:
#         delete_disabled = confirm_input.strip() != doc_type.strip()
#         if st.button(
#             "🗑️ Delete this document",
#             use_container_width=True,
#             type="primary",
#             disabled=delete_disabled,
#         ):
#             st.session_state[f"do_delete_{doc_id}"] = True
#             st.rerun()
#     with col2:
#         if st.button("Cancel", use_container_width=True):
#             st.rerun()

# #