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

# def render_sidebar():
#     logger.debug("Rendering sidebar")
#     with st.sidebar:
#         st.markdown(
#             "<h1 style='color:white;text-align:center;margin-bottom:15px;'>📄 DocForgeHub</h1>",
#             unsafe_allow_html=True,
#         )

#         # Backend health indicator
#         is_up = _is_backend_up()
#         logger.debug(f"Backend health check: {'UP' if is_up else 'DOWN'}")
#         color = "#4CAF50" if is_up else "#f44336"
#         label = "🟢 Backend Connected" if is_up else "🔴 Backend Offline"
#         st.markdown(
#             f"<div style='background:{color};padding:7px;border-radius:8px;"
#             f"text-align:center;color:white;font-size:.85rem;margin-bottom:12px;'>{label}</div>",
#             unsafe_allow_html=True,
#         )

#         if not is_up:
#             st.markdown(
#                 "<div style='color:#ffd700;font-size:.78rem;text-align:center;padding:6px;'>"
#                 "Run: <code>uvicorn main:app --reload</code></div>",
#                 unsafe_allow_html=True,
#             )

#         # Reset offline warning on reconnect
#         if is_up:
#             st.session_state["_backend_offline_shown"] = False

#         st.markdown("<hr style='border:1px solid rgba(255,255,255,.3);'>", unsafe_allow_html=True)

#         pages = {
#             "🏠 Home": "Home",
#             "✨ Generate": "Generate",
#             "📚 Library": "Library",
#             "🗂 Templates": "Templates",
#             "❓ Questionnaires": "Questionnaires",
#             "🚀 Publish to Notion": "Notion",
#             "📊 Stats": "Stats",
#         }
#         for page_label, key in pages.items():
#             if st.button(page_label, key=f"nav_{key}", use_container_width=True):
#                     logger.info(f"Navigating to page: {key}")
#                     st.session_state.page = key
#                     st.rerun()
            
#                     st.markdown("<hr style='border:1px solid rgba(255,255,255,.3);margin:10px 0;'>", unsafe_allow_html=True)
#                     st.markdown("<p style='color:#C4B5FD;font-size:.75rem;text-align:center;font-weight:700;letter-spacing:.12em;'>🤖 AI ASSISTANT</p>", unsafe_allow_html=True)
#                     if st.button("🤖 AI Assistant", key="nav_AI Assistant", use_container_width=True):
#                         st.session_state.page = "AI Assistant"
#                         st.rerun()

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

        if is_up:
            st.session_state["_backend_offline_shown"] = False

        st.markdown("<hr style='border:1px solid rgba(255,255,255,.3);'>", unsafe_allow_html=True)

        # ── Main navigation pages ────────────────────────────────────────
        pages = {
            "🏠 Home":              "Home",
            "✨ Generate":          "Generate",
            "📚 Library":           "Library",
            "🗂 Templates":         "Templates",
            "❓ Questionnaires":    "Questionnaires",
            "🚀 Publish to Notion": "Notion",
            "📊 Stats":             "Stats",
        }
        for page_label, key in pages.items():
            if st.button(page_label, key=f"nav_{key}", use_container_width=True):
                logger.info(f"Navigating to page: {key}")
                st.session_state.page = key
                st.rerun()

        # ── AI Assistant section ─────────────────────────────────────────
        # THIS BLOCK must be at the same indent level as the for loop above
        # NOT inside the if st.button block
        st.markdown(
            "<hr style='border:1px solid rgba(255,255,255,.3);margin:10px 0;'>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='color:#C4B5FD;font-size:.75rem;text-align:center;"
            "font-weight:700;letter-spacing:.12em;'>🤖 AI ASSISTANT</p>",
            unsafe_allow_html=True,
        )
        if st.button("🤖 AI Assistant", key="nav_ai_assistant", use_container_width=True):
            st.session_state.page = "AI Assistant"
            st.rerun()

        st.markdown("<hr style='border:1px solid rgba(255,255,255,.3);margin:15px 0;'>", unsafe_allow_html=True)

        # ── Live stats ───────────────────────────────────────────────────
        if is_up:
            stats = get_stats()
            if stats:
                st.markdown("<h3 style='color:white;'>📊 Live Stats</h3>", unsafe_allow_html=True)
                st.metric("Templates", stats.get("templates", 0))
                st.metric("Documents", stats.get("documents_generated", 0))
                st.metric("Jobs Done", stats.get("jobs_completed", 0))

        st.markdown(
            "<div style='color:rgba(255,255,255,.6);text-align:center;font-size:.75rem;margin-top:25px;'>"
            "Powered by Azure OpenAI<br>© 2026 DocForgeHub</div>",
            unsafe_allow_html=True,
        )

        st.markdown("<hr style='border:1px solid rgba(255,255,255,.3);margin:10px 0;'>",
            unsafe_allow_html=True)
        st.markdown("<p style='color:#C4B5FD;font-size:.75rem;text-align:center;"
                    "font-weight:700;letter-spacing:.12em;'>🤖 PROJECT 3</p>",
                    unsafe_allow_html=True)
        if st.button("🤖 Stateful Assistant", key="nav_assistant", use_container_width=True):
            st.session_state.page = "Assistant"
            st.rerun()

        # # ── Project 2 — RAG AI Assistant ─────────────────────────
        # st.markdown(
        #     "<hr style='border:1px solid rgba(255,255,255,.3);margin:10px 0;'>",
        #     unsafe_allow_html=True,
        # )
        # st.markdown(
        #     "<p style='color:#C4B5FD;font-size:.78rem;text-align:center;"
        #     "font-weight:600;letter-spacing:.08em;'>🤖 AI ASSISTANT</p>",
        #     unsafe_allow_html=True,
        # )
        # if st.button("🤖 AI Assistant", key="nav_ai", use_container_width=True):
        #     st.session_state.page = "AI Assistant"
        #     st.rerun()

        # st.markdown(
        #     "<hr style='border:1px solid rgba(255,255,255,.3);margin:15px 0;'>",
        #     unsafe_allow_html=True,
        # )

        # st.markdown(
        #     "<hr style='border:1px solid rgba(255,255,255,.3);margin:15px 0;'>",
        #     unsafe_allow_html=True,
        # )

        # if is_up:
        #     stats = get_stats()
        #     if stats:
        #         logger.debug(f"Stats: {stats.get('templates')} templates, {stats.get('documents_generated')} docs")
        #         st.markdown("<h3 style='color:white;'>📊 Live Stats</h3>", unsafe_allow_html=True)
        #         st.metric("Templates", stats.get("templates", 0))
        #         st.metric("Documents", stats.get("documents_generated", 0))
        #         st.metric("Jobs Done", stats.get("jobs_completed", 0))

        # st.markdown(
        #     "<div style='color:rgba(255,255,255,.6);text-align:center;font-size:.75rem;margin-top:25px;'>"
        #     "Powered by Azure OpenAI<br>© 2026 DocForgeHub</div>",
        #     unsafe_allow_html=True,
        # )


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
    import time
    logger.info("Rendering page: Generate")

    # ── CSS ──────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    /* Progress stepper */
    .stepper-wrap{display:flex;align-items:center;justify-content:center;margin:20px 0 30px;gap:0;}
    .step-item{display:flex;flex-direction:column;align-items:center;position:relative;flex:1;max-width:200px;}
    .step-circle{width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;
        font-size:1.1rem;font-weight:700;z-index:2;position:relative;transition:all .3s;}
    .step-done  .step-circle{background:linear-gradient(135deg,#4CAF50,#45a049);color:white;box-shadow:0 4px 15px rgba(76,175,80,.4);}
    .step-active .step-circle{background:linear-gradient(135deg,#667eea,#764ba2);color:white;box-shadow:0 4px 20px rgba(102,126,234,.5);
        animation:pulse-ring 1.5s infinite;}
    .step-pending .step-circle{background:#e8e8e8;color:#aaa;}
    .step-label{font-size:.75rem;font-weight:600;margin-top:8px;text-align:center;
        color:#4CAF50;letter-spacing:.03em;}
    .step-active .step-label{color:#667eea;}
    .step-pending .step-label{color:#bbb;}
    .step-line{flex:1;height:3px;margin-top:-30px;z-index:1;}
    .step-line-done{background:linear-gradient(90deg,#4CAF50,#667eea);}
    .step-line-pending{background:#e8e8e8;}

    /* Animated progress bar */
    .prog-bar-wrap{background:#f0f0f0;border-radius:20px;height:8px;margin:0 0 28px;overflow:hidden;box-shadow:inset 0 2px 4px rgba(0,0,0,.06);}
    .prog-bar-fill{height:100%;border-radius:20px;background:linear-gradient(90deg,#667eea,#764ba2,#667eea);
        background-size:200% 100%;animation:shimmer 2s linear infinite;transition:width .6s ease;}
    @keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
    @keyframes pulse-ring{0%{box-shadow:0 0 0 0 rgba(102,126,234,.5)}70%{box-shadow:0 0 0 10px rgba(102,126,234,0)}100%{box-shadow:0 0 0 0 rgba(102,126,234,0)}}

    /* Step cards */
    .gen-card{background:white;border-radius:16px;padding:28px 32px;border:1.5px solid #E8E0FF;
        box-shadow:0 4px 20px rgba(102,126,234,.08);margin-bottom:20px;}
    .gen-card-title{font-size:1.3rem;font-weight:700;color:#1e3c72;margin-bottom:6px;display:flex;align-items:center;gap:10px;}
    .gen-card-sub{font-size:.88rem;color:#888;margin-bottom:20px;}

    /* Question block */
    .q-card{background:#FAFBFF;border-left:4px solid #667eea;border-radius:0 10px 10px 0;
        padding:12px 16px;margin-bottom:10px;}
    .q-card.required{border-left-color:#f44336;}
    .q-label{font-size:.88rem;font-weight:600;color:#1e3c72;margin-bottom:6px;}
    .q-req{color:#f44336;font-size:.75rem;margin-left:6px;}

    /* Success banner */
    .success-banner{background:linear-gradient(135deg,#11998e,#38ef7d);color:white;
        border-radius:14px;padding:16px 22px;text-align:center;font-weight:700;
        font-size:1rem;margin-bottom:20px;box-shadow:0 6px 20px rgba(17,153,142,.3);}

    /* Metric cards */
    .metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px;}
    .metric-card{border-radius:14px;padding:20px 16px;text-align:center;color:white;
        box-shadow:0 6px 20px rgba(0,0,0,.12);transition:transform .2s;}
    .metric-card:hover{transform:translateY(-3px);}
    .metric-num{font-size:2rem;font-weight:800;line-height:1.1;}
    .metric-lbl{font-size:.68rem;letter-spacing:2px;text-transform:uppercase;opacity:.88;margin-top:5px;}
    .metric-sub{display:flex;gap:20px;justify-content:center;margin-top:8px;}
    .metric-sub-item{text-align:center;}
    .metric-sub-num{font-size:1.6rem;font-weight:700;}
    .metric-sub-lbl{font-size:.62rem;letter-spacing:1.5px;text-transform:uppercase;opacity:.85;}
    .metric-divider{width:1px;background:rgba(255,255,255,.35);align-self:stretch;}

    /* Doc preview */
    .doc-preview{background:#FAFAFA;border:1.5px solid #E8E0FF;border-radius:12px;
        padding:24px 28px;max-height:500px;overflow-y:auto;line-height:1.8;font-size:.92rem;}
    .doc-preview::-webkit-scrollbar{width:6px;}
    .doc-preview::-webkit-scrollbar-thumb{background:#C5CAE9;border-radius:3px;}

    /* Edit section card */
    .edit-card{background:linear-gradient(135deg,#E8EAF6,#F3E5F5);border-radius:14px;
        padding:20px 24px;border:1.5px solid #C5CAE9;margin-bottom:16px;}
    .edit-card-title{font-weight:700;color:#1e3c72;font-size:1rem;margin-bottom:4px;}
    .edit-card-sub{font-size:.82rem;color:#666;margin-bottom:14px;}

    /* Action buttons */
    .stButton > button{border-radius:10px !important;font-weight:600 !important;
        transition:all .2s !important;border:none !important;}

    /* Category header */
    .cat-header{background:linear-gradient(135deg,#667eea15,#764ba215);border-radius:10px;
        padding:10px 16px;margin:20px 0 12px;border-left:4px solid #667eea;}
    .cat-header-text{font-weight:700;color:#1e3c72;font-size:.95rem;}

    /* Info pill */
    .info-pill{background:linear-gradient(135deg,#E3F2FD,#E8EAF6);border-radius:10px;
        padding:10px 16px;border:1px solid #C5CAE9;font-size:.85rem;color:#283593;margin-bottom:16px;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 class='main-header'>✨ Generate New Document</h1>", unsafe_allow_html=True)

    step = st.session_state.gen_step

    # ── Animated progress bar ─────────────────────────────────────────────
    pct = {1: 5, 2: 50, 3: 100}[step]
    st.markdown(f"""
    <div class="prog-bar-wrap">
        <div class="prog-bar-fill" style="width:{pct}%"></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Step stepper ──────────────────────────────────────────────────────
    steps_info = [
        ("📋", "Select Type"),
        ("❓", "Answer Questions"),
        ("🎉", "Generate & Review"),
    ]
    stepper_html = '<div class="stepper-wrap">'
    for i, (icon, label) in enumerate(steps_info):
        cls = "step-done" if i + 1 < step else ("step-active" if i + 1 == step else "step-pending")
        check = "✅" if i + 1 < step else icon
        stepper_html += f'<div class="step-item {cls}"><div class="step-circle">{check}</div><div class="step-label">{label}</div></div>'
        if i < len(steps_info) - 1:
            line_cls = "step-line-done" if i + 1 < step else "step-line-pending"
            stepper_html += f'<div class="step-line {line_cls}"></div>'
    stepper_html += '</div>'
    st.markdown(stepper_html, unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # STEP 1 — Select Type
    # ════════════════════════════════════════════════════════════════════
    if step == 1:
        st.markdown("""
        <div class="gen-card">
            <div class="gen-card-title">📋 Select Document Type</div>
            <div class="gen-card-sub">Choose your department and the document you want to generate</div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            industry = st.selectbox("🏢 Industry", ["SaaS"], key="s1_ind")
        with c2:
            dept = st.selectbox("🏛️ Department", DEPARTMENTS, key="s1_dept")
        with c3:
            dept_docs = get_doc_types_for_dept(dept)
            dtype = st.selectbox("📄 Document Type", dept_docs, key="s1_type")

        # Section preview
        schema_data = api_get("/questionnaires/schema",
                              params={"department": dept, "document_type": dtype})
        if schema_data and schema_data.get("sections"):
            sections = schema_data["sections"]
            pills = "".join(
                f"<span style='background:#EDE7F6;color:#4A148C;padding:3px 10px;"
                f"border-radius:20px;font-size:.75rem;margin:2px;display:inline-block;'>{s}</span>"
                for s in sections[:6]
            )
            more = f"<span style='color:#aaa;font-size:.78rem;'> +{len(sections)-6} more</span>" if len(sections) > 6 else ""
            st.markdown(
                f"<div class='info-pill'>📋 <b>{dtype}</b> — {len(sections)} sections:<br>{pills}{more}</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➡️ Next: Answer Questions", use_container_width=True, type="primary"):
            st.session_state.sel_industry = industry
            st.session_state.sel_dept     = dept
            st.session_state.sel_type     = dtype
            st.session_state.gen_step     = 2
            st.rerun()

    # ════════════════════════════════════════════════════════════════════
    # STEP 2 — Answer Questions
    # ════════════════════════════════════════════════════════════════════
    elif step == 2:
        dept  = st.session_state.sel_dept
        dtype = st.session_state.sel_type

        st.markdown(f"""
        <div class="gen-card">
            <div class="gen-card-title">❓ Answer Questions</div>
            <div class="gen-card-sub">Generating: <b>{dtype}</b> for <b>{dept}</b></div>
        </div>
        """, unsafe_allow_html=True)

        questions = get_questions(dept, dtype)
        answers   = {}

        cats: dict = {}
        for q in questions:
            cats.setdefault(q.get("category", "common"), []).append(q)

        cat_labels = {
            "common":                 ("📋", "General Questions"),
            "metadata":               ("🗂️", "Document Metadata"),
            "metadata_questions":     ("🗂️", "Document Metadata"),
            "document_type_specific": ("📄", f"{dtype} — Specific Questions"),
            "department_specific":    ("🏛️", f"{dept} — Specific Questions"),
        }

        for cat, qs in cats.items():
            if not qs:
                continue
            icon, label = cat_labels.get(cat, ("❓", cat.replace("_", " ").title()))
            st.markdown(
                f'<div class="cat-header"><span class="cat-header-text">{icon} {label}</span></div>',
                unsafe_allow_html=True,
            )
            for q in qs:
                qid   = q.get("id", "")
                qtext = q.get("question", "")
                qtype = q.get("type", "text")
                qreq  = q.get("required", False)
                qopts = q.get("options", [])

                req_badge = '<span class="q-req">* Required</span>' if qreq else ""
                st.markdown(
                    f'<div class="q-card {"required" if qreq else ""}">'
                    f'<div class="q-label">{qtext}{req_badge}</div></div>',
                    unsafe_allow_html=True,
                )
                wkey = f"qa_{qid}"
                if qtype == "text":
                    answers[qid] = st.text_input("v", key=wkey, label_visibility="collapsed")
                elif qtype == "textarea":
                    answers[qid] = st.text_area("v", key=wkey, height=90, label_visibility="collapsed")
                elif qtype == "date":
                    answers[qid] = str(st.date_input("v", key=wkey, label_visibility="collapsed"))
                elif qtype == "number":
                    answers[qid] = str(st.number_input("v", key=wkey, step=1, label_visibility="collapsed"))
                elif qtype == "select" and qopts:
                    answers[qid] = st.selectbox("v", ["(select)"] + qopts, key=wkey, label_visibility="collapsed")
                elif qtype in ("multi_select", "multiselect") and qopts:
                    answers[qid] = st.multiselect("v", qopts, key=wkey, label_visibility="collapsed")
                else:
                    answers[qid] = st.text_input("v", key=wkey, label_visibility="collapsed")

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state.gen_step = 1
                st.rerun()
        with c2:
            if st.button("🚀 Generate Document", use_container_width=True, type="primary"):
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

    # ════════════════════════════════════════════════════════════════════
    # STEP 3 — Generate & Review
    # ════════════════════════════════════════════════════════════════════
    elif step == 3:

        if st.session_state.last_doc is None:
            # ── Animated generation progress ──────────────────────────
            st.markdown("""
            <div class="gen-card">
                <div class="gen-card-title">⚙️ Generating Your Document</div>
                <div class="gen-card-sub">Azure OpenAI is building your document section by section…</div>
            </div>
            """, unsafe_allow_html=True)

            progress_steps = [
                ("🔗 Connecting to FastAPI backend…",            0.12),
                ("📋 Loading template from database…",           0.28),
                ("❓ Loading questionnaire schema…",             0.44),
                ("🧠 Building AI prompt…",                       0.60),
                ("⚡ Calling Azure OpenAI (30-60s)…",            0.82),
                ("✅ Validating and saving document…",            0.95),
            ]

            pb      = st.progress(0)
            status  = st.empty()

            for txt, pct in progress_steps:
                status.markdown(
                    f"<div style='text-align:center;padding:12px;background:#F5F3FF;"
                    f"border-radius:10px;color:#667eea;font-weight:600;font-size:.95rem;'>{txt}</div>",
                    unsafe_allow_html=True,
                )
                pb.progress(pct)
                time.sleep(0.3)

            payload = {
                "industry":         st.session_state.sel_industry,
                "department":       st.session_state.sel_dept,
                "document_type":    st.session_state.sel_type,
                "question_answers": st.session_state.qa,
            }
            logger.info(f"Generating: {payload['document_type']} | {payload['department']}")
            result = api_post("/documents/generate", payload)

            pb.progress(1.0)
            status.empty()
            pb.empty()

            if result:
                st.session_state.last_doc = result
            else:
                st.markdown("""
                <div style='background:#FFEBEE;border-left:4px solid #f44336;border-radius:10px;
                    padding:16px 20px;margin:16px 0;'>
                    <b style='color:#B71C1C;'>❌ Document generation failed</b><br>
                    <span style='color:#C62828;font-size:.88rem;'>
                    Check backend is running · Azure credentials in .env · Backend logs for details
                    </span>
                </div>
                """, unsafe_allow_html=True)
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
        pc     = len(v.get("passed", []))
        ic     = len(v.get("issues", []))

        # ── Success banner ────────────────────────────────────────────
        st.markdown(
            f"<div class='success-banner'>✅ Document Generated Successfully! &nbsp;|&nbsp; "
            f"ID: {doc_id} &nbsp;|&nbsp; Job: {str(doc.get('job_id',''))[:8]}…</div>",
            unsafe_allow_html=True,
        )

        if st.session_state.get("_show_comparison"):
            st.info("🎯 Regenerated document — compare quality scores below!")

        # ── Metric cards ──────────────────────────────────────────────
        score_bg = (
            "linear-gradient(135deg,#11998e,#38ef7d)" if score >= 75
            else "linear-gradient(135deg,#f7971e,#ffd200)" if score >= 60
            else "linear-gradient(135deg,#f44336,#ff6b6b)"
        )
        checks_bg = (
            "linear-gradient(135deg,#f44336,#ff6b6b)" if ic > 0
            else "linear-gradient(135deg,#667eea,#764ba2)"
        )

        st.markdown(f"""
        <div class="metric-grid">
            <div class="metric-card" style="background:{score_bg};">
                <div class="metric-num">{score}/100</div>
                <div class="metric-lbl">Quality Score</div>
            </div>
            <div class="metric-card" style="background:{score_bg};">
                <div class="metric-num">{grade}</div>
                <div class="metric-lbl">Grade</div>
            </div>
            <div class="metric-card" style="background:linear-gradient(135deg,#667eea,#764ba2);">
                <div class="metric-num">{wc:,}</div>
                <div class="metric-lbl">Words</div>
            </div>
            <div class="metric-card" style="background:{checks_bg};">
                <div class="metric-sub">
                    <div class="metric-sub-item">
                        <div class="metric-sub-num">{pc}</div>
                        <div class="metric-sub-lbl">Pass</div>
                    </div>
                    <div class="metric-divider"></div>
                    <div class="metric-sub-item">
                        <div class="metric-sub-num">{ic}</div>
                        <div class="metric-sub-lbl">Fail</div>
                    </div>
                </div>
                <div class="metric-lbl">Checks</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # ── Document preview + Edit Sections tabs ─────────────────────
        t1, t2 = st.tabs(["📖 Full Document", "✏️ Edit Sections"])

        with t1:
            doc_content = doc.get("document", "No content available.")
            st.markdown(
                f'<div class="doc-preview">{doc_content}</div>',
                unsafe_allow_html=True,
            )

        with t2:
            st.markdown("""
            <div class="edit-card">
                <div class="edit-card-title">✏️ Edit Specific Sections</div>
                <div class="edit-card-sub">Edit any section of your document and preview changes in real-time.</div>
            </div>
            """, unsafe_allow_html=True)

            doc_content = doc.get("document", "")
            lines = doc_content.split('\n')
            sections = {}
            current_heading = None
            current_content = []

            for line in lines:
                if line.startswith('## ') and not line.startswith('### '):
                    if current_heading:
                        sections[current_heading] = '\n'.join(current_content).strip()
                    current_heading = line[3:].strip()
                    current_content = []
                elif line.startswith('# ') and not line.startswith('## '):
                    if current_heading:
                        sections[current_heading] = '\n'.join(current_content).strip()
                    current_heading = line[2:].strip()
                    current_content = []
                else:
                    current_content.append(line)
            if current_heading:
                sections[current_heading] = '\n'.join(current_content).strip()

            if not sections:
                st.info("ℹ️ No sections found. Document may use a different heading format.")
                edited = st.text_area(
                    "Edit full document:", value=doc_content, height=400, key="full_edit"
                )
                if st.button("💾 Save Changes", use_container_width=True, type="primary"):
                    if "last_doc" in st.session_state and st.session_state.last_doc:
                        st.session_state.last_doc["document"] = edited
                        st.success("✅ Changes saved!")
                        st.rerun()
            else:
                st.markdown(
                    f"<div class='info-pill'>💡 Click on a section below to edit it. "
                    f"<b>{len(sections)} sections</b> found.</div>",
                    unsafe_allow_html=True,
                )

                edited_sections = {}
                for heading, content in sections.items():
                    with st.expander(f"✏️ {heading}", expanded=False):
                        edited_text = st.text_area(
                            f"Edit {heading}:",
                            value=content,
                            height=200,
                            key=f"edit_{heading[:30]}",
                            label_visibility="collapsed",
                        )
                        edited_sections[heading] = edited_text

                if st.button("💾 Save All Section Edits", use_container_width=True, type="primary"):
                    new_content = []
                    for heading, content in edited_sections.items():
                        new_content.append(f"## {heading}")
                        new_content.append(content)
                        new_content.append("")
                    st.session_state.last_doc["document"] = '\n'.join(new_content)
                    st.success("✅ All sections saved! Switch to 'Full Document' tab to preview.")
                    st.rerun()

        # ── Submitted Answers ─────────────────────────────────────────
        with st.expander("📋 Your Submitted Answers"):
            st.json(st.session_state.qa)

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # ── Download ──────────────────────────────────────────────────
        st.markdown("""
        <div style='font-size:1.1rem;font-weight:700;color:#1e3c72;margin-bottom:1px;'>
            📥 Download & Export
        </div>
        """, unsafe_allow_html=True)
        full_doc = api_get(f"/documents/{doc_id}")
        render_download_buttons(
            doc_id,
            st.session_state.sel_type,
            st.session_state.sel_dept,
            full_doc,
            key_prefix="gen",
        )

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # ── Action buttons ────────────────────────────────────────────
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🔄 Regenerate Document", use_container_width=True):
                with st.spinner("🔄 Regenerating…"):
                    try:
                        regen = api_post(f"/documents/regenerate/{doc_id}", {})
                        if regen:
                            st.session_state.last_doc = {
                                "job_id":      regen.get("regen_job_id"),
                                "document_id": regen.get("regenerated_document_id"),
                                "document":    regen.get("document"),
                                "validation":  regen.get("validation", {}),
                            }
                            st.session_state["_show_comparison"] = True
                            st.success(f"✅ Regenerated! New ID: {regen.get('regenerated_document_id')}")
                            st.rerun()
                        else:
                            st.error("❌ Regeneration failed.")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
        with c2:
            if st.button("✨ Generate Another", use_container_width=True):
                st.session_state.gen_step = 1
                st.session_state.last_doc = None
                st.session_state.qa       = {}
                st.rerun()
        with c3:
            if st.button("📚 Go to Library", use_container_width=True):
                st.session_state.page     = "Library"
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
                meta  = full.get("metadata", {})
                _raw  = full.get("generated_content", "No content available")
                wc    = meta.get('word_count') or len(_raw.split())

                st.markdown(
                    f"<div style='background:#f8f9fa;border:1px solid #e0e0e0;"
                    f"border-radius:10px;padding:10px 18px;margin:8px 0;font-size:.85rem;'>"
                    f"📄 <b>#{doc.get('id')} — {full.get('document_type')}</b> &nbsp;|&nbsp; "
                    f"🏛️ {full.get('department')} &nbsp;|&nbsp; "
                    f"📝 {wc} words</div>",
                    unsafe_allow_html=True,
                )

                # CSS for controlled sizing
                st.markdown("""
                <style>
                .lib-doc h1{font-size:1.6rem!important;font-weight:700!important;color:#1e3c72!important;
                border-bottom:2px solid #667eea;padding-bottom:8px;margin:20px 0 12px!important;}

                .lib-doc h2{font-size:1.35rem!important;font-weight:600!important;color:#2a5298!important;
                margin:18px 0 10px!important;}

                .lib-doc h3{font-size:1.15rem!important;font-weight:600!important;color:#444!important;
                margin:14px 0 8px!important;}

                .lib-doc p{font-size:15px!important;line-height:1.8!important;
                margin:8px 0!important;color:#2c2c2c!important;}

                .lib-doc li{font-size:15px!important;line-height:1.8!important;
                color:#2c2c2c!important;margin:3px 0!important;}

                .lib-doc strong,.lib-doc b{font-weight:600!important;
                color:#1e3c72!important;font-size:15px!important;}

                .lib-doc em{font-style:italic!important;color:#555!important;}

                .lib-doc table{width:100%!important;border-collapse:collapse!important;
                font-size:14px!important;margin:14px 0!important;
                border:1px solid #e0e0e0!important;border-radius:8px!important;}

                .lib-doc th{background:linear-gradient(135deg,#667eea,#764ba2)!important;
                color:white!important;padding:10px 14px!important;
                text-align:left!important;font-size:14px!important;font-weight:600!important;}

                .lib-doc td{padding:9px 14px!important;border-bottom:1px solid #f0f0f0!important;
                font-size:14px!important;color:#333!important;}

                .lib-doc tr:nth-child(even) td{background:#f8f9ff!important;}
                .lib-doc tr:hover td{background:#f0f4ff!important;}

                .lib-doc hr{border:none!important;border-top:1.5px solid #e8e0ff!important;
                margin:18px 0!important;}

                .lib-doc code{background:#f4f4f4!important;padding:2px 8px!important;
                border-radius:4px!important;font-size:13.5px!important;color:#d63384!important;}

                .lib-doc blockquote{border-left:4px solid #667eea!important;
                padding:8px 16px!important;margin:12px 0!important;
                background:#f8f9ff!important;border-radius:0 8px 8px 0!important;
                color:#555!important;font-style:italic!important;}
                </style>
                """, unsafe_allow_html=True)

                # Markdown properly convert karo HTML mein
                import re

                def md_to_html(text):
                    # Tables preserve karo
                    lines      = text.split('\n')
                    html_lines = []
                    i          = 0
                    while i < len(lines):
                        line = lines[i]

                        # Table detection
                        if '|' in line and i + 1 < len(lines) and '|' in lines[i+1] and '---' in lines[i+1]:
                            table_lines = [line]
                            i += 2  # skip separator
                            while i < len(lines) and '|' in lines[i]:
                                table_lines.append(lines[i])
                                i += 1
                            # Build table HTML
                            html_lines.append('<table>')
                            for j, tline in enumerate(table_lines):
                                cells = [c.strip() for c in tline.strip().strip('|').split('|')]
                                tag   = 'th' if j == 0 else 'td'
                                html_lines.append('<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>')
                            html_lines.append('</table>')
                            continue

                        # Headings
                        if line.startswith('### '):
                            html_lines.append(f'<h3>{line[4:].strip()}</h3>')
                        elif line.startswith('## '):
                            html_lines.append(f'<h2>{line[3:].strip()}</h2>')
                        elif line.startswith('# '):
                            html_lines.append(f'<h1>{line[2:].strip()}</h1>')
                        # HR
                        elif line.strip() in ('---', '***', '___'):
                            html_lines.append('<hr>')
                        # Bullet
                        elif line.startswith('- ') or line.startswith('* '):
                            content = line[2:].strip()
                            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
                            html_lines.append(f'<li>{content}</li>')
                        # Numbered
                        elif re.match(r'^\d+\. ', line):
                            content = re.sub(r'^\d+\. ', '', line).strip()
                            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
                            html_lines.append(f'<li>{content}</li>')
                        # Empty line
                        elif line.strip() == '':
                            html_lines.append('<br>')
                        # Normal paragraph
                        else:
                            content = line.strip()
                            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
                            content = re.sub(r'\*(.+?)\*',     r'<em>\1</em>',         content)
                            content = re.sub(r'`(.+?)`',       r'<code>\1</code>',     content)
                            html_lines.append(f'<p>{content}</p>')
                        i += 1

                    return '\n'.join(html_lines)

                html_content = md_to_html(_raw)

                st.markdown(
                    f"<div class='lib-doc' style='background:white;border:1px solid #e0e0e0;"
                    f"border-radius:12px;padding:24px 32px;margin:8px 0;"
                    f"max-height:650px;overflow-y:auto;"
                    f"box-shadow:0 2px 8px rgba(0,0,0,.06);'>"
                    f"{html_content}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                if st.button("✖ Close View", key=f"close_{doc_id}"):
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



# ============================================================
# STEP 1 — Add these constants in document_app.py
# Place right after:  ALL_DOC_TYPES = sorted({...})
# ============================================================

ALL_INDUSTRIES = ["SaaS",]

ALL_VERSIONS = ["v1", "v2", "v3", "v4", "v5"]


# ============================================================
# STEP 2 — Replace your entire page_rag_chat() with this
# ============================================================
import uuid as _uuid
  
def page_rag_assistant():
    # ── Session init ─────────────────────────────────────────
    for k, v in {
        "rag_sid":       _uuid.uuid4().hex[:8],
        "rag_history":   [],
        "rag_tab":       "chat",
        "rag_eval_tab":  "compare",
        "search_done":   None,
        "refine_done":   None,
        "compare_done":  None,
        "eval_result":   None,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v
 
    # ── CSS ──────────────────────────────────────────────────
    st.markdown("""
<style>
.rag-hero{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:16px;
  padding:28px 32px;color:white;text-align:center;margin-bottom:20px;
  box-shadow:0 8px 32px rgba(102,126,234,.35);}
.rag-hero h1{font-size:2rem;font-weight:800;margin:0 0 6px;}
.rag-hero p{font-size:.92rem;opacity:.88;margin:0;}
.rag-msg-user{background:#E3F2FD;border-radius:16px 16px 4px 16px;padding:13px 17px;
  margin:8px 0;border-left:4px solid #1976D2;}
.rag-msg-bot{background:linear-gradient(135deg,#F3E5F5 0%,#EDE7F6 100%);
  border-radius:16px 16px 16px 4px;padding:13px 17px;margin:8px 0;border-left:4px solid #7B1FA2;}
.rag-cite{background:#E8F5E9;border:1px solid #A5D6A7;border-radius:8px;
  padding:7px 12px;margin:3px 0;font-size:.82rem;color:#1B5E20;}
.rag-chunk{background:white;border:1.5px solid #E8E0FF;border-radius:12px;
  padding:15px;margin:8px 0;box-shadow:0 2px 8px rgba(0,0,0,.05);}
.rag-meta-pill{display:inline-block;background:#EDE7F6;color:#4A148C;
  padding:2px 10px;border-radius:20px;font-size:.73rem;font-weight:600;margin:2px;}
.rag-score-bar{height:5px;border-radius:3px;margin-top:8px;}
.rag-compare-card{background:white;border-radius:12px;padding:16px;
  border-top:4px solid;box-shadow:0 3px 12px rgba(0,0,0,.08);}
.rag-eval-card{border-radius:13px;padding:18px 12px;text-align:center;color:white;
  min-height:88px;display:flex;flex-direction:column;align-items:center;justify-content:center;}
.rag-eval-num{font-size:1.9rem;font-weight:800;}
.rag-eval-lbl{font-size:.7rem;opacity:.88;letter-spacing:1.5px;text-transform:uppercase;}
.rag-empty{background:#FAFBFF;border:2px dashed #C5CAE9;border-radius:14px;
  padding:36px 24px;text-align:center;color:#888;}
.rag-refine-box{background:linear-gradient(135deg,#E8F5E9,#F1F8E9);
  border:1.5px solid #81C784;border-radius:10px;padding:13px 16px;margin:8px 0;}
.rag-info-strip{background:linear-gradient(135deg,#E3F2FD,#E8EAF6);border-radius:10px;
  padding:10px 14px;margin-bottom:14px;font-size:.83rem;color:#283593;}
.rag-section-header{background:white;border-radius:12px;padding:14px 18px;
  border:1.5px solid #E8E0FF;margin-bottom:14px;}
</style>
""", unsafe_allow_html=True)
 
    # ── Hero ─────────────────────────────────────────────────
    st.markdown("""
<div class="rag-hero">
  <h1>🤖 RAG Assistant</h1>
  <p>Notion-powered knowledge base &nbsp;·&nbsp; Chat &nbsp;·&nbsp; Search &nbsp;·&nbsp; Compare &nbsp;·&nbsp; Evaluate</p>
</div>
""", unsafe_allow_html=True)
 
    # ── Tab buttons ──────────────────────────────────────────
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        if st.button("💬  Chat", key="rtab_chat", use_container_width=True,
                     type="primary" if st.session_state.rag_tab == "chat" else "secondary"):
            st.session_state.rag_tab = "chat"
            st.rerun()
    with tc2:
        if st.button("🔍  Search & Inspect", key="rtab_search", use_container_width=True,
                     type="primary" if st.session_state.rag_tab == "search" else "secondary"):
            st.session_state.rag_tab = "search"
            st.rerun()
    with tc3:
        if st.button("📊  Evaluation", key="rtab_eval", use_container_width=True,
                     type="primary" if st.session_state.rag_tab == "eval" else "secondary"):
            st.session_state.rag_tab = "eval"
            st.rerun()
 
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
 
    # ════════════════════════════════════════════════════════
    # CHAT TAB
    # ════════════════════════════════════════════════════════
    if st.session_state.rag_tab == "chat":
        # Info strip
        st.markdown(
            f"<div class='rag-info-strip'>"
            f"📚 <b>910 chunks</b> from <b>129 Notion docs</b> &nbsp;·&nbsp; "
            f"Session: <code>{st.session_state.rag_sid}</code> &nbsp;·&nbsp; "
            f"<b>{len(st.session_state.rag_history)//2}</b> messages</div>",
            unsafe_allow_html=True,
        )
 
        # Filters
        fc1, fc2 = st.columns(2)
        with fc1:
            f_dept = st.selectbox("🏛️ Department", ["All"] + DEPARTMENTS, key="cf_dept")
        with fc2:
            f_type = st.selectbox("📄 Doc Type", ["All"] + ALL_DOC_TYPES, key="cf_type")
        filters = {}
        if f_dept != "All": filters["department"] = f_dept
        if f_type != "All": filters["doc_type"]   = f_type
 
        # Example questions grid
        st.markdown("<p style='color:#888;font-size:.82rem;margin:12px 0 6px;'>💡 <b>Example questions:</b></p>", unsafe_allow_html=True)
        examples = [
            ("📋", "Create a compliant incident response summary per our policy"),
            ("⚖️", "Compare SOW vs MSA clauses"),
            ("🔒", "What are NDA confidentiality obligations?"),
            ("📈", "Summarise the SLA uptime requirements"),
            ("👤", "What does the HR leave policy say?"),
            ("🛡️", "What's in the Data Processing Agreement?"),
        ]
        picked = ""
        row1 = st.columns(3)
        row2 = st.columns(3)
        for i, (icon, ex) in enumerate(examples):
            col = row1[i] if i < 3 else row2[i-3]
            with col:
                if st.button(f"{icon} {ex}", key=f"cex_{i}", use_container_width=True):
                    picked = ex
 
        st.markdown("<br>", unsafe_allow_html=True)
 
        # Chat history
        if st.session_state.rag_history:
            for msg in st.session_state.rag_history:
                if msg["role"] == "user":
                    st.markdown(
                        f"<div class='rag-msg-user'>👤 <b>You</b><br>{msg['content']}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div class='rag-msg-bot'>🤖 <b>DocForge AI</b><br><br>{msg['content']}</div>",
                        unsafe_allow_html=True,
                    )
                    if msg.get("citations"):
                        with st.expander(f"📎 {len(msg['citations'])} Source(s)", expanded=False):
                            for cit in msg["citations"]:
                                # dict ya string dono handle karo
                                if isinstance(cit, dict):
                                    doc   = cit.get("doc_title", cit.get("doc_type", "Unknown"))
                                    sec   = cit.get("section", "")
                                    score = cit.get("score", 0)
                                    label = f"{doc} › {sec}" if sec else doc
                                    pct   = f" · {float(score):.0%}" if score else ""
                                    display = f"{label}{pct}"
                                else:
                                    display = str(cit)
                                st.markdown(
                                    f"<div class='rag-cite'>📄 {display}</div>",
                                    unsafe_allow_html=True,
                                )
                    if msg.get("refined"):
                        st.markdown(
                            f"<div class='rag-refine-box'>✨ <b>Refined query:</b> {msg['refined']}</div>",
                            unsafe_allow_html=True,
                        )
        else:
            st.markdown("""
<div class='rag-empty'>
  <div style='font-size:2.8rem;margin-bottom:10px;'>🧠</div>
  <b style='font-size:1rem;'>Ask anything about your documents</b><br>
  <span style='font-size:.85rem;'>Your Notion knowledge base is ready.<br>Try one of these examples or type your own question below.</span>
</div>""", unsafe_allow_html=True)
 
        # Input row
        st.markdown("<br>", unsafe_allow_html=True)
        qi1, qi2 = st.columns([9, 1])
        with qi1:
            user_q = st.text_input(
            "Q",
            placeholder="Ask anything about your documents…",
            key="chat_q", label_visibility="collapsed",
        )
        with qi2:
            send_btn = st.button("↑", key="chat_send", use_container_width=True, type="primary")
 
        # final_q = picked if picked else (user_q.strip() if send_btn and user_q.strip() else "")

        if picked:
            final_q = picked
        elif send_btn and user_q.strip():
            final_q = user_q.strip()
        else:
            final_q = ""

        # input clear karo after send
        if final_q and send_btn:
            # st.session_state["chat_q"] = ""
 
        # if final_q:
        #     with st.spinner("🔍 Searching 910 chunks across 129 documents…"):
        #         payload = {"question": final_q, "session_id": st.session_state.rag_sid,
        #                    "use_refine": True, "top_k": 5}
        #         payload.update(filters)
        #         result = api_post("/rag/answer", payload)
 
        #     if result and result.get("success"):
        #         refined = result.get("refined_query", "")
        #         st.session_state.rag_history.append({"role": "user", "content": final_q})
        #         st.session_state.rag_history.append({
        #             "role":      "assistant",
        #             "content":   result["answer"],
        #             "citations": result.get("citations", []),
        #             "refined":   refined if refined != final_q else "",
        #         })
        #         st.rerun()
            if final_q:
             # Step 1 — user message PEHLE save karo
                st.session_state.rag_history.append({
                    "role":    "user",
                    "content": final_q,
                })

            # Step 2 — API call
            with st.spinner("🔍 Searching knowledge base…"):
                payload = {
                    "question":   final_q,
                    "session_id": st.session_state.rag_sid,
                    "use_refine": True,
                    "top_k":      5,
                }
                payload.update(filters)
                result = api_post("/rag/answer", payload)

            # Step 3 — assistant message save karo
            if result and result.get("success"):
                refined = result.get("refined_query", "")
                st.session_state.rag_history.append({
                    "role":      "assistant",
                    "content":   result["answer"],
                    "citations": result.get("citations", []),
                    "refined":   refined if refined != final_q else "",
                })
            else:
                st.session_state.rag_history.append({
                    "role":      "assistant",
                    "content":   "⚠️ Could not retrieve an answer. Please try again.",
                    "citations": [],
                    "refined":   "",
                })

            if "chat_q" in st.session_state:
                # st.session_state["chat_q"] = ""
                pass

            # Step 4 — rerun BAAD mein
            st.rerun()
 
        if st.session_state.rag_history:
            if st.button("🗑️ Clear Chat", key="chat_clear", use_container_width=True):
                api_post(f"/rag/session/{st.session_state.rag_sid}", {})  
                st.session_state.rag_history = []
                st.session_state.rag_sid     = _uuid.uuid4().hex[:8]
                st.rerun()
 
    # ════════════════════════════════════════════════════════
    # SEARCH TAB
    # ════════════════════════════════════════════════════════
    elif st.session_state.rag_tab == "search":
        st.markdown("""
<div class='rag-section-header'>
  <b style='color:#1e3c72;'>🔍 Smart Search &amp; Retrieval Inspector</b><br>
  <span style='color:#888;font-size:.83rem;'>Inspect retrieved chunks, scores, and metadata in real time</span>
</div>""", unsafe_allow_html=True)
 
        sq = st.text_input(
            "Query",
            placeholder="e.g. termination clause, service uptime, confidentiality obligations…",
            key="sq_input", label_visibility="collapsed",
        )
 
        sf1, sf2, sf3, sf4 = st.columns([3, 3, 2, 1])
        with sf1:
            sd  = st.selectbox("Dept",    ["All"] + DEPARTMENTS,  key="sf_dept", label_visibility="collapsed")
        with sf2:
            st2 = st.selectbox("Type",    ["All"] + ALL_DOC_TYPES, key="sf_type", label_visibility="collapsed")
        with sf3:
            sk  = st.number_input("Top K", 1, 15, 5, key="sf_k",   label_visibility="collapsed")
        with sf4:
            sv  = st.selectbox("Ver",     ["All","v1","v2","v3"],  key="sf_ver",  label_visibility="collapsed")
 
        sb1, sb2 = st.columns(2)
        with sb1:
            search_clicked = st.button("🔍 Search Knowledge Base", use_container_width=True, key="sq_btn", type="primary")
        with sb2:
            refine_clicked = st.button("✨ AI Query Refiner",       use_container_width=True, key="sq_ref")
 
        if search_clicked and sq.strip():
            payload = {"query": sq.strip(), "top_k": int(sk)}
            if sd  != "All": payload["department"] = sd
            if st2 != "All": payload["doc_type"]   = st2
            if sv  != "All": payload["version"]    = sv
            with st.spinner("Searching…"):
                st.session_state.search_done = api_post("/rag/retrieve", payload)
 
        if refine_clicked and sq.strip():
            with st.spinner("Refining…"):
                st.session_state.refine_done = api_post("/rag/refine", {"query": sq.strip(), "context": ""})
 
        # Refine result
        if st.session_state.refine_done:
            r = st.session_state.refine_done
            if r.get("success"):
                ra, rb = st.columns(2)
                with ra:
                    st.markdown(
                        f"<div style='background:#F3E5F5;border-left:4px solid #7B1FA2;"
                        f"border-radius:8px;padding:12px 15px;margin:8px 0;'>"
                        f"<p style='color:#4A148C;font-weight:700;font-size:.78rem;margin:0 0 4px;'>ORIGINAL</p>"
                        f"<p style='margin:0;'>{r['original']}</p></div>",
                        unsafe_allow_html=True,
                    )
                with rb:
                    st.markdown(
                        f"<div style='background:#E8F5E9;border-left:4px solid #4CAF50;"
                        f"border-radius:8px;padding:12px 15px;margin:8px 0;'>"
                        f"<p style='color:#1B5E20;font-weight:700;font-size:.78rem;margin:0 0 4px;'>REFINED ✨</p>"
                        f"<p style='margin:0;font-weight:600;'>{r['refined']}</p></div>",
                        unsafe_allow_html=True,
                    )
                if r.get("keywords"):
                    kw = " ".join([
                        f"<span style='background:#1976D2;color:white;padding:2px 9px;"
                        f"border-radius:12px;font-size:.76rem;margin:2px;display:inline-block;'>{k}</span>"
                        for k in r["keywords"]
                    ])
                    st.markdown(
                        f"<div style='background:#E3F2FD;border-radius:8px;padding:10px 14px;margin:6px 0;'>"
                        f"🔑 <b>Keywords:</b> {kw}</div>",
                        unsafe_allow_html=True,
                    )
                if r.get("suggestions"):
                    st.markdown("<b style='color:#555;font-size:.82rem;'>💡 Try also:</b>", unsafe_allow_html=True)
                    for s in r["suggestions"]:
                        st.markdown(
                            f"<div style='background:#FAFAFA;border:1px solid #E0E0E0;"
                            f"border-radius:6px;padding:7px 12px;margin:3px 0;font-size:.85rem;'>→ {s}</div>",
                            unsafe_allow_html=True,
                        )
 
        # Search results
        if st.session_state.search_done:
            res    = st.session_state.search_done
            chunks = res.get("chunks", [])
            cached = res.get("cached", False)
 
            st.markdown(
                f"<div style='background:linear-gradient(135deg,#667eea,#764ba2);color:white;"
                f"padding:10px 16px;border-radius:10px;margin:14px 0;"
                f"display:flex;justify-content:space-between;align-items:center;'>"
                f"<span><b>{len(chunks)}</b> chunks retrieved</span>"
                f"<span style='font-size:.8rem;opacity:.9;'>{'⚡ From cache' if cached else '🔍 Fresh search'}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
 
            if not chunks:
                st.markdown(
                    "<div class='rag-empty'><div style='font-size:2rem;'>🔎</div>"
                    "<b>No chunks found</b><br><span style='font-size:.85rem;'>Try different keywords or remove filters</span></div>",
                    unsafe_allow_html=True,
                )
            else:
                for i, chunk in enumerate(chunks, 1):
                    meta  = chunk.get("metadata", {})
                    score = chunk.get("score", 0)
                    pct   = int(score * 100)
                    bar_c = "#4CAF50" if score > 0.7 else "#FF9800" if score > 0.5 else "#f44336"
 
                    ca, cb = st.columns([8, 2])
                    with ca:
                        st.markdown(
                            f"<div class='rag-chunk'>"
                            f"<div style='display:flex;justify-content:space-between;margin-bottom:8px;'>"
                            f"<b style='color:#1e3c72;'>#{i} — {chunk.get('citation','')}</b>"
                            f"<span style='background:#EDE7F6;color:#4A148C;padding:2px 8px;"
                            f"border-radius:10px;font-size:.72rem;'>ID: {chunk.get('id','')[:10]}…</span>"
                            f"</div>"
                            f"<div style='margin-bottom:8px;'>"
                            f"<span class='rag-meta-pill'>🏛️ {meta.get('department','—')}</span>"
                            f"<span class='rag-meta-pill'>📄 {meta.get('doc_type','—')}</span>"
                            f"<span class='rag-meta-pill'>🏭 {meta.get('industry','—')}</span>"
                            f"<span class='rag-meta-pill'>🔖 {meta.get('version','—')}</span>"
                            f"</div>"
                            f"<div style='color:#333;font-size:.87rem;line-height:1.65;'>"
                            f"{chunk.get('text','')[:420]}{'…' if len(chunk.get('text',''))>420 else ''}"
                            f"</div>"
                            f"<div class='rag-score-bar' style='background:{bar_c};width:{pct}%;'></div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    with cb:
                        lbl_c = "#2E7D32" if score > 0.7 else "#E65100" if score > 0.5 else "#B71C1C"
                        bg_c  = "#E8F5E9" if score > 0.7 else "#FFF3E0" if score > 0.5 else "#FFEBEE"
                        lbl   = "High ✓" if score > 0.7 else "Medium" if score > 0.5 else "Low"
                        st.markdown(
                            f"<div style='text-align:center;padding-top:22px;'>"
                            f"<div style='font-size:1.7rem;font-weight:800;color:{bar_c};'>{pct}%</div>"
                            f"<div style='font-size:.72rem;color:#999;margin:2px 0;'>relevance</div>"
                            f"<div style='background:{bg_c};border-radius:6px;padding:3px 8px;"
                            f"font-size:.72rem;font-weight:700;color:{lbl_c};'>{lbl}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
 
    # ════════════════════════════════════════════════════════
    # EVALUATION TAB
    # ════════════════════════════════════════════════════════
    elif st.session_state.rag_tab == "eval":
        st.markdown("""
<div class='rag-section-header'>
  <b style='color:#1e3c72;'>📊 Evaluation Dashboard</b><br>
  <span style='color:#888;font-size:.83rem;'>Compare documents and measure RAG pipeline quality with RAGAS</span>
</div>""", unsafe_allow_html=True)
 
        # Sub-tab buttons
        et1, et2 = st.columns(2)
        with et1:
            if st.button("⚖️ Compare Docs", key="et_cmp", use_container_width=True,
                         type="primary" if st.session_state.rag_eval_tab == "compare" else "secondary"):
                st.session_state.rag_eval_tab = "compare"
                st.rerun()
        with et2:
            if st.button("📈 RAGAS Eval", key="et_rag", use_container_width=True,
                         type="primary" if st.session_state.rag_eval_tab == "ragas" else "secondary"):
                st.session_state.rag_eval_tab = "ragas"
                st.rerun()
 
        st.markdown("<br>", unsafe_allow_html=True)
 
        # ── Compare sub ────────────────────────────────────
        if st.session_state.rag_eval_tab == "compare":
            st.markdown(
                "<div style='background:#F5F3FF;border-radius:10px;padding:12px 15px;margin-bottom:14px;'>"
                "<b style='color:#4A148C;'>⚖️ Side-by-side Document Comparison</b><br>"
                "<span style='color:#666;font-size:.83rem;'>Select two document types and a question — "
                "see how RAG answers differ across them.</span></div>",
                unsafe_allow_html=True,
            )
 
            da1, da2 = st.columns(2)
            with da1:
                st.markdown("<p style='color:#666;font-size:.83rem;margin-bottom:4px;'>📘 Document A</p>", unsafe_allow_html=True)
                doc_a = st.selectbox("Doc A", ALL_DOC_TYPES, key="cmp_a", label_visibility="collapsed")
            with da2:
                st.markdown("<p style='color:#666;font-size:.83rem;margin-bottom:4px;'>📗 Document B</p>", unsafe_allow_html=True)
                doc_b = st.selectbox("Doc B", ALL_DOC_TYPES, index=min(1, len(ALL_DOC_TYPES)-1), key="cmp_b", label_visibility="collapsed")
 
            st.markdown("<p style='color:#666;font-size:.83rem;margin:10px 0 4px;'>❓ Comparison question</p>", unsafe_allow_html=True)
            cmp_q = st.text_input("Cmp Q",
                                  placeholder="What are the key obligations and limitations?",
                                  key="cmp_q", label_visibility="collapsed")
 
            # Quick topic pills
            st.markdown("<p style='color:#aaa;font-size:.78rem;margin:6px 0 4px;'>Quick topics:</p>", unsafe_allow_html=True)
            tpc = st.columns(5)
            for i, t in enumerate(["termination clauses", "liability", "payment terms", "confidentiality", "dispute resolution"]):
                with tpc[i]:
                    if st.button(t, key=f"tp_{i}", use_container_width=True):
                        st.session_state["_cmp_sel"] = t
                        st.rerun()
            if "_cmp_sel" in st.session_state:
                cmp_q = st.session_state["_cmp_sel"]
 
            if st.button("⚖️ Run Comparison", use_container_width=True, key="cmp_run", type="primary"):
                if doc_a == doc_b:
                    st.warning("⚠️ Please select two different document types!")
                elif not cmp_q.strip():
                    st.warning("⚠️ Please enter a comparison question!")
                else:
                    with st.spinner(f"Comparing {doc_a} vs {doc_b}…"):
                        st.session_state.compare_done = api_post("/rag/compare", {
                            "query": cmp_q.strip(), "doc_type_a": doc_a,
                            "doc_type_b": doc_b, "session_id": st.session_state.rag_sid,
                        })
 
            if st.session_state.compare_done:
                r = st.session_state.compare_done
                if r and r.get("success"):
                    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

                    # Doc A vs Doc B — clearly different content
                    ca2, cb2 = st.columns(2)
                    with ca2:
                        st.markdown(
                            f"<div style='background:linear-gradient(135deg,#E3F2FD,#E8EAF6);"
                            f"border-radius:12px;padding:16px;border-left:4px solid #1976D2;'>"
                            f"<p style='font-weight:700;color:#0D47A1;font-size:.95rem;margin:0 0 10px;'>"
                            f"📘 {r['doc_a']['type']}</p>",
                            unsafe_allow_html=True,
                        )
                        for cit in r["doc_a"]["citations"]:
                            st.markdown(f"<div class='rag-cite'>📄 {cit}</div>", unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                        for pt in r["doc_a"].get("points", []):
                            st.markdown(
                                f"<p style='font-size:.85rem;color:#333;margin:5px 0;'>• {pt}</p>",
                                unsafe_allow_html=True,
                            )
                        st.markdown("</div>", unsafe_allow_html=True)

                with cb2:
                    st.markdown(
                        f"<div style='background:linear-gradient(135deg,#F3E5F5,#EDE7F6);"
                        f"border-radius:12px;padding:16px;border-left:4px solid #7B1FA2;'>"
                        f"<p style='font-weight:700;color:#4A148C;font-size:.95rem;margin:0 0 10px;'>"
                        f"📗 {r['doc_b']['type']}</p>",
                        unsafe_allow_html=True,
                    )
                    for cit in r["doc_b"]["citations"]:
                        st.markdown(
                            f"<div class='rag-cite' style='border-color:#7B1FA2;background:#F3E5F5;color:#4A148C;'>"
                            f"📄 {cit}</div>",
                            unsafe_allow_html=True,
                        )
                    st.markdown("<br>", unsafe_allow_html=True)
                    for pt in r["doc_b"].get("points", []):
                        st.markdown(
                            f"<p style='font-size:.85rem;color:#333;margin:5px 0;'>• {pt}</p>",
                            unsafe_allow_html=True,
                        )
                    st.markdown("</div>", unsafe_allow_html=True)

                # Similarities and Differences
                st.markdown("<br>", unsafe_allow_html=True)
                s1, s2 = st.columns(2)
                with s1:
                    st.markdown(
                        "<div style='background:#E8F5E9;border-radius:12px;padding:16px;"
                        "border-left:4px solid #4CAF50;'>"
                        "<p style='font-weight:700;color:#1B5E20;margin:0 0 10px;'>✅ Similarities</p>",
                        unsafe_allow_html=True,
                    )
                    for sim in r.get("similarities", []):
                        st.markdown(
                            f"<p style='font-size:.85rem;color:#1B5E20;margin:5px 0;'>• {sim}</p>",
                            unsafe_allow_html=True,
                        )
                    st.markdown("</div>", unsafe_allow_html=True)

                with s2:
                    st.markdown(
                        "<div style='background:#FFEBEE;border-radius:12px;padding:16px;"
                        "border-left:4px solid #f44336;'>"
                        "<p style='font-weight:700;color:#B71C1C;margin:0 0 10px;'>⚡ Key Differences</p>",
                        unsafe_allow_html=True,
                    )
                    for diff in r.get("differences", []):
                        st.markdown(
                            f"<p style='font-size:.85rem;color:#B71C1C;margin:5px 0;'>• {diff}</p>",
                            unsafe_allow_html=True,
                        )
                    st.markdown("</div>", unsafe_allow_html=True)

                # Recommendation
                if r.get("recommendation"):
                    st.markdown(
                        f"<div style='background:linear-gradient(135deg,#667eea,#764ba2);"
                        f"border-radius:12px;padding:16px;margin-top:12px;color:white;'>"
                        f"<p style='font-weight:700;margin:0 0 6px;'>💡 Recommendation</p>"
                        f"<p style='font-size:.88rem;opacity:.95;margin:0;'>{r['recommendation']}</p>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
 
        # ── RAGAS sub ──────────────────────────────────────
        else:
            left, right = st.columns(2, gap="large")
 
            with left:
                st.markdown("<h3 style='color:#1e3c72;font-size:1rem;margin-bottom:10px;'>🚀 Run Evaluation</h3>", unsafe_allow_html=True)
                ek = st.slider("Top K chunks", 1, 10, 5, key="ev_k")
                er = st.checkbox("Use query refinement", value=True, key="ev_r")
                st.markdown(
                    "<div style='background:#F5F3FF;border-radius:8px;padding:10px 13px;"
                    "border:1px solid #E8E0FF;margin:8px 0;font-size:.82rem;color:#4A148C;'>"
                    "📋 <b>Default:</b> 5 questions — NDA, SLA, HR Policy, Data Breach, Vendor Contracts</div>",
                    unsafe_allow_html=True,
                )
                with st.expander("➕ Custom Test Questions"):
                    custom_qs = st.text_area(
                        "question | ground_truth",
                        placeholder="What are NDA obligations? | Receiving party must protect info.",
                        height=80, key="ev_cq",
                    )
 
                if st.button("🚀 Run RAGAS Evaluation", use_container_width=True, key="ev_run", type="primary"):
                    dataset = []
                    cq = st.session_state.get("ev_cq", "")
                    if cq.strip():
                        for line in cq.strip().split("\n"):
                            if "|" in line:
                                p = line.split("|", 1)
                                dataset.append({"question": p[0].strip(), "ground_truth": p[1].strip()})
                            elif line.strip():
                                dataset.append({"question": line.strip(), "ground_truth": ""})
                    res = api_post("/rag/eval/run", {
                        "top_k": ek, "use_refine": er,
                        "save_results": True, "filters": {}, "dataset": dataset,
                    })
                    if res and res.get("success"):
                        st.success(f"✅ {res['message']}")
                        st.info("⏳ Results ready in ~2 min. Click 'Load Results' →")
 
            with right:
                st.markdown("<h3 style='color:#1e3c72;font-size:1rem;margin-bottom:10px;'>📈 Results</h3>", unsafe_allow_html=True)
                if st.button("🔄 Load Latest Results", use_container_width=True, key="ev_load"):
                    res = api_get("/rag/eval/results")
                    if res and res.get("success") and res.get("results"):
                        st.session_state.eval_result = res["results"]
                    else:
                        st.info("No results yet — run evaluation first!")
 
                if st.session_state.eval_result:
                    data   = st.session_state.eval_result
                    scores = data.get("scores", {})
                    ov     = scores.get("overall", 0)
                    ov_c   = "#4CAF50" if ov > 0.7 else "#FF9800" if ov > 0.5 else "#f44336"
                    st.markdown(
                        f"<div style='background:{ov_c};border-radius:12px;padding:14px;"
                        f"text-align:center;color:white;margin-bottom:12px;'>"
                        f"<div style='font-size:2rem;font-weight:800;'>{ov:.1%}</div>"
                        f"<div style='font-size:.82rem;opacity:.9;'>Overall RAGAS Score</div></div>",
                        unsafe_allow_html=True,
                    )
                    sc_items = [
                        ("faithfulness",      "Faithfulness",      "#667eea"),
                        ("answer_relevancy",  "Answer Relevancy",  "#764ba2"),
                        ("context_precision", "Context Precision", "#4facfe"),
                        ("context_recall",    "Context Recall",    "#11998e"),
                    ]
                    r1, r2 = st.columns(2)
                    for i, (key, lbl, clr) in enumerate(sc_items):
                        val = scores.get(key, 0)
                        with (r1 if i % 2 == 0 else r2):
                            st.markdown(
                                f"<div class='rag-eval-card' style='background:{clr};margin:4px 0;'>"
                                f"<div class='rag-eval-num'>{val:.1%}</div>"
                                f"<div class='rag-eval-lbl'>{lbl}</div></div>",
                                unsafe_allow_html=True,
                            )
                    st.markdown(
                        f"<p style='color:#aaa;font-size:.76rem;text-align:center;margin-top:6px;'>"
                        f"📅 {data.get('timestamp','')[:16]} · {data.get('dataset_size',0)} questions</p>",
                        unsafe_allow_html=True,
                    )
 
            # Per-question detail
            if st.session_state.eval_result:
                st.markdown("<hr class='divider'>", unsafe_allow_html=True)
                st.markdown("<h3 style='color:#1e3c72;font-size:1rem;'>📋 Per-Question Results</h3>", unsafe_allow_html=True)
                for i, item in enumerate(st.session_state.eval_result.get("results", []), 1):
                    with st.expander(f"Q{i}: {item['question'][:65]}…"):
                        qa3, qb3 = st.columns(2)
                        with qa3:
                            st.markdown(f"**❓ Question:**\n{item['question']}")
                            if item.get("ground_truth"):
                                st.markdown(f"**✅ Ground Truth:**\n{item['ground_truth']}")
                        with qb3:
                            st.markdown(f"**🤖 AI Answer:**\n{item.get('answer','N/A')[:350]}…")
                            if item.get("citations"):
                                for cit in item["citations"]:
                                    st.markdown(f"<div class='rag-cite'>📄 {cit}</div>", unsafe_allow_html=True)
                        st.markdown(
                            f"<p style='color:#aaa;font-size:.78rem;'>"
                            f"Chunks: {item.get('chunks_used',0)} · Refined: {item.get('refined_query','—')}</p>",
                            unsafe_allow_html=True,
                        )
 
            # History
            st.markdown("<hr class='divider'>", unsafe_allow_html=True)
            if st.button("📜 Evaluation History", use_container_width=True, key="ev_hist"):
                res = api_get("/rag/eval/history")
                if res and res.get("history"):
                    import pandas as pd
                    rows = []
                    for h in res["history"]:
                        s = h.get("scores", {})
                        rows.append({
                            "Timestamp":         h.get("timestamp","")[:16],
                            "Overall":           f"{s.get('overall',0):.1%}",
                            "Faithfulness":      f"{s.get('faithfulness',0):.1%}",
                            "Answer Relevancy":  f"{s.get('answer_relevancy',0):.1%}",
                            "Context Precision": f"{s.get('context_precision',0):.1%}",
                            "Context Recall":    f"{s.get('context_recall',0):.1%}",
                            "Questions":         h.get("dataset_size", 0),
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)
                else:
                    st.info("No history yet.")


def page_assistant():
    """
    Project 3 — Stateful RAG Assistant with Notion Ticketing
    Add to document_app.py and call from main() when page == "Assistant"
    Also add to render_sidebar() nav buttons.
    """
    import uuid

    ALL_INDUSTRIES = ["SaaS", ]

    # ── Session init ─────────────────────────────────────────────────────
    for k, v in {
        "asst_thread_id":  None,
        "asst_history":    [],
        "asst_tab":        "chat",
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ── CSS ──────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .asst-hero{background:linear-gradient(135deg,#1e3c72 0%,#667eea 60%,#764ba2 100%);
        border-radius:18px;padding:28px 32px;color:white;margin-bottom:24px;}
    .asst-hero h1{font-size:2rem;font-weight:800;margin:0 0 6px;}
    .asst-hero p{font-size:.92rem;opacity:.88;margin:0;}
    .msg-user{background:#E3F2FD;border-radius:16px 16px 4px 16px;
        padding:13px 17px;margin:8px 0;border-left:4px solid #1976D2;}
    .msg-bot{background:linear-gradient(135deg,#F3E5F5,#EDE7F6);
        border-radius:16px 16px 16px 4px;padding:13px 17px;margin:8px 0;border-left:4px solid #7B1FA2;}
    .msg-label{font-size:.75rem;font-weight:700;text-transform:uppercase;
        letter-spacing:.08em;margin-bottom:5px;opacity:.75;}
    .cite-pill{display:inline-block;background:#E8F5E9;border:1px solid #A5D6A7;
        border-radius:20px;padding:3px 10px;font-size:.78rem;color:#1B5E20;margin:2px;}
    .ticket-banner{background:linear-gradient(135deg,#FF6B6B,#EE5A24);
        border-radius:12px;padding:14px 18px;color:white;margin:10px 0;}
    .ticket-banner b{font-size:1rem;}
    .ticket-row{display:flex;gap:8px;align-items:center;padding:8px 0;
        border-bottom:1px solid #f0f0f0;font-size:.88rem;}
    .ticket-row:last-child{border:none;}
    .status-badge{padding:3px 10px;border-radius:12px;font-size:.75rem;font-weight:700;}
    .status-open{background:#FFE0E0;color:#C0392B;}
    .status-progress{background:#FFF3E0;color:#E67E22;}
    .status-resolved{background:#E8F5E9;color:#27AE60;}
    .status-closed{background:#F5F5F5;color:#666;}
    .empty-asst{background:#FAFBFF;border:2px dashed #C5CAE9;border-radius:14px;
        padding:36px 24px;text-align:center;color:#888;}
    .thread-badge{display:inline-flex;align-items:center;gap:6px;
        background:#EDE7F6;border-radius:20px;padding:4px 12px;
        font-size:.78rem;color:#4A148C;font-weight:600;}
    </style>
    """, unsafe_allow_html=True)

    # ── Hero ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="asst-hero">
        <h1>🤖 Stateful Assistant</h1>
        <p>Remembers your context · Answers from knowledge base · Creates Notion tickets when it can't</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Tab buttons ───────────────────────────────────────────────────────
    tc1, tc2 = st.columns(2)
    with tc1:
        if st.button("💬 Chat", key="atab_chat", use_container_width=True,
                     type="primary" if st.session_state.asst_tab == "chat" else "secondary"):
            st.session_state.asst_tab = "chat"
            st.rerun()
    with tc2:
        if st.button("🎫 My Tickets", key="atab_tickets", use_container_width=True,
                     type="primary" if st.session_state.asst_tab == "tickets" else "secondary"):
            st.session_state.asst_tab = "tickets"
            st.rerun()

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # CHAT TAB
    # ════════════════════════════════════════════════════════════════════
    if st.session_state.asst_tab == "chat":

        # ── Start / resume thread ─────────────────────────────────────
        if not st.session_state.asst_thread_id:
            st.markdown("""
            <div class="empty-asst">
                <div style="font-size:2.8rem;margin-bottom:10px;">🤖</div>
                <b style="font-size:1rem;">Start a new conversation</b><br>
                <span style="font-size:.85rem;">Set your context and start chatting below</span>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                industry = st.selectbox("🏢 Industry", ["All"] + ALL_INDUSTRIES,
                                        key="asst_industry")
            with c2:
                dept = st.selectbox("🏛️ Department", ["All"] + DEPARTMENTS,
                                    key="asst_dept")

            if st.button("🚀 Start Conversation", use_container_width=True, type="primary"):
                result = api_post("/assistant/threads", {
                    "user_id":    "user_001",
                    "industry":   None if industry == "All" else industry,
                    "department": None if dept == "All" else dept,
                })
                if result and result.get("success"):
                    st.session_state.asst_thread_id = result["thread_id"]
                    st.session_state.asst_history   = []
                    st.rerun()
                else:
                    st.error("❌ Could not create thread. Check backend.")
            return

        # ── Thread info ───────────────────────────────────────────────
        st.markdown(
            f'<div class="thread-badge">🔑 Thread: {st.session_state.asst_thread_id}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        # ── Render history ────────────────────────────────────────────
        for msg in st.session_state.asst_history:
            if msg["role"] == "user":
                st.markdown(
                    f"<div class='msg-user'>"
                    f"<div class='msg-label'>You</div>{msg['content']}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='msg-bot'>"
                    f"<div class='msg-label'>Assistant</div>{msg['content']}</div>",
                    unsafe_allow_html=True,
                )
                if msg.get("citations"):
                    cites = "".join(
                        f"<span class='cite-pill'>📄 {c}</span>"
                        for c in msg["citations"]
                    )
                    st.markdown(
                        f"<div style='margin-top:6px;'>{cites}</div>",
                        unsafe_allow_html=True,
                    )
                if msg.get("ticket_url"):
                    st.markdown(
                        f"<div class='ticket-banner'>"
                        f"<b>🎫 Ticket Created</b><br>"
                        f"<a href='{msg['ticket_url']}' target='_blank' "
                        f"style='color:white;'>View in Notion →</a></div>",
                        unsafe_allow_html=True,
                    )

        # ── Input ─────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        qi1, qi2 = st.columns([9, 1])
        with qi1:
            user_msg = st.text_input(
                "msg", placeholder="Ask anything… e.g. 'What are NDA obligations?'",
                key="asst_input", label_visibility="collapsed",
            )
        with qi2:
            send = st.button("↑", key="asst_send", use_container_width=True,
                             type="primary")

        if send and user_msg.strip():
            with st.spinner("🔍 Thinking…"):
                result = api_post("/assistant/chat", {
                    "thread_id": st.session_state.asst_thread_id,
                    "message":   user_msg.strip(),
                    "user_id":   "user_001",
                })

            if result and result.get("success"):
                st.session_state.asst_history.append(
                    {"role": "user", "content": user_msg.strip()}
                )
                st.session_state.asst_history.append({
                    "role":       "assistant",
                    "content":    result.get("answer", ""),
                    "citations":  result.get("citations", []),
                    "ticket_url": result.get("notion_url"),
                })
                st.rerun()
            else:
                st.error("❌ Assistant error. Check backend logs.")

        # ── Footer ────────────────────────────────────────────────────
        if st.session_state.asst_history:
            if st.button("🗑️ End Conversation", use_container_width=True):
                api_post(f"/assistant/threads/{st.session_state.asst_thread_id}",
                         {}, method="DELETE") if False else None
                st.session_state.asst_thread_id = None
                st.session_state.asst_history   = []
                st.rerun()

    # ════════════════════════════════════════════════════════════════════
    # TICKETS TAB
    # ════════════════════════════════════════════════════════════════════
    else:
        st.markdown("### 🎫 Support Tickets")

        # Stats
        stats = api_get("/tickets/stats")
        if stats:
            sc1, sc2, sc3, sc4 = st.columns(4)
            bs = stats.get("by_status", {})
            for col, lbl, key, color in [
                (sc1, "Total",       "total",       "#667eea"),
                (sc2, "Open",        "open",        "#f44336"),
                (sc3, "In Progress", "in_progress", "#FF9800"),
                (sc4, "Resolved",    "resolved",    "#4CAF50"),
            ]:
                with col:
                    val = stats.get("total") if key == "total" else bs.get(key, 0)
                    st.markdown(
                        f"<div style='background:{color};color:white;border-radius:12px;"
                        f"padding:14px;text-align:center;'>"
                        f"<div style='font-size:1.8rem;font-weight:700;'>{val}</div>"
                        f"<div style='font-size:.72rem;opacity:.9;text-transform:uppercase;"
                        f"letter-spacing:1.5px;'>{lbl}</div></div>",
                        unsafe_allow_html=True,
                    )

        st.markdown("<br>", unsafe_allow_html=True)

        # Filters
        fc1, fc2 = st.columns(2)
        with fc1:
            f_status = st.selectbox("Filter Status",
                                    ["All", "open", "in_progress", "resolved", "closed"])
        with fc2:
            f_dept = st.selectbox("Filter Department", ["All"] + DEPARTMENTS)

        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

        # Tickets list
        params = {}
        if f_status != "All": params["status"]     = f_status
        if f_dept   != "All": params["department"] = f_dept
        tickets_res = api_get("/tickets/", params=params)
        tickets     = tickets_res.get("tickets", []) if tickets_res else []

        if not tickets:
            st.info("No tickets found.")
        else:
            for t in tickets:
                status = t.get("status", "open")
                status_cls = {
                    "open": "status-open",
                    "in_progress": "status-progress",
                    "resolved":    "status-resolved",
                    "closed":      "status-closed",
                }.get(status, "status-open")

                with st.expander(
                    f"🎫 #{t['id']} — {t['question'][:60]}… | {t.get('priority','medium').upper()}"
                ):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Question:** {t['question']}")
                        st.markdown(f"**Department:** {t.get('department','—')}")
                        st.markdown(f"**Owner:** {t.get('assigned_owner','—')}")
                        st.markdown(f"**Created:** {str(t.get('created_at',''))[:16]}")
                    with c2:
                        st.markdown(
                            f"<span class='status-badge {status_cls}'>"
                            f"{status.replace('_',' ').upper()}</span>",
                            unsafe_allow_html=True,
                        )
                        if t.get("evidence_score"):
                            st.caption(f"Evidence score: {t['evidence_score']:.3f}")
                        if t.get("notion_url"):
                            st.link_button("🔗 View in Notion", t["notion_url"])

                    # Status update
                    new_status = st.selectbox(
                        "Update status",
                        ["open", "in_progress", "resolved", "closed"],
                        index=["open","in_progress","resolved","closed"].index(
                            status if status in ["open","in_progress","resolved","closed"] else "open"
                        ),
                        key=f"ts_{t['id']}",
                    )
                    if st.button("💾 Update", key=f"tu_{t['id']}"):
                        res = api_post(f"/tickets/{t['id']}/status",
                                       {"status": new_status}, method="PUT")
                        if res and res.get("success"):
                            st.success(f"✅ Status updated to: {new_status}")
                            st.rerun()
 
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
    elif page == "AI Assistant": page_rag_assistant()
    elif page == "Assistant": page_assistant()
    # elif page == "AI Assistant":   page_rag_chat()
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
