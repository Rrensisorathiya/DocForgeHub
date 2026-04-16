"""
notion_service.py — Complete Notion Integration for DocForgeHub
===============================================================
• Fixes "Name is not a property" error
• Creates beautiful, richly formatted Notion pages
• Supports full markdown → Notion blocks conversion
• Auto-sets up DB properties if missing
• Attractive callout boxes, dividers, color-coded sections
"""

import os
import re
import requests
from typing import Optional
from datetime import datetime
from document_app import NOTION_API_URL, notion_headers
from services.notion_service import (
    notion_publish,
    notion_update_page,
    check_notion_page_exists,  # ← yeh add karo
)

NOTION_VERSION = "2022-06-28"

from utils.logger import setup_logger

logger = setup_logger(__name__)

logger.info("Connecting to Notion API")


# ══════════════════════════════════════════════════════════════
# CORE CLIENT
# ══════════════════════════════════════════════════════════════

class NotionClient:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }
        self.base = "https://api.notion.com/v1"

    def get(self, path: str) -> dict:
        r = requests.get(f"{self.base}{path}", headers=self.headers)
        return r.json()

    def post(self, path: str, body: dict) -> dict:
        r = requests.post(f"{self.base}{path}", headers=self.headers, json=body)
        return r.json()

    def patch(self, path: str, body: dict) -> dict:
        r = requests.patch(f"{self.base}{path}", headers=self.headers, json=body)
        return r.json()


# ══════════════════════════════════════════════════════════════
# DB PROPERTY INSPECTOR — detects real property names
# ══════════════════════════════════════════════════════════════

def get_db_properties(client: NotionClient, db_id: str) -> dict:
    """Returns {prop_name: prop_type} for the database."""
    data = client.get(f"/databases/{db_id}")
    props = data.get("properties", {})
    return {name: info["type"] for name, info in props.items()}


def find_title_property(props: dict) -> str:
    """Find which property is the title (there's always exactly one)."""
    for name, ptype in props.items():
        if ptype == "title":
            return name
    return "Title"





# ══════════════════════════════════════════════════════════════
# DB SETUP — ensure all needed properties exist
# ══════════════════════════════════════════════════════════════

REQUIRED_PROPERTIES = {
    "Department": {"select": {"options": [
        {"name": "HR & People Operations", "color": "pink"},
        {"name": "Legal & Compliance", "color": "blue"},
        {"name": "Sales & Customer Facing", "color": "green"},
        {"name": "Engineering & Operations", "color": "orange"},
        {"name": "Product & Design", "color": "purple"},
        {"name": "Marketing & Content", "color": "yellow"},
        {"name": "Finance & Operations", "color": "red"},
        {"name": "IT & Internal Systems", "color": "gray"},
        {"name": "Data & Analytics", "color": "brown"},
        {"name": "QA & Testing", "color": "default"},
        {"name": "Security & Information Assurance", "color": "red"},
        {"name": "Platform & Infrastructure Operations", "color": "blue"},
        {"name": "Partnership & Alliances", "color": "green"},
    ]}},
    "Document Type": {"select": {"options": [
        # HR & People Operations
        {"name": "Offer Letter", "color": "pink"},
        {"name": "Employment Contract", "color": "pink"},
        {"name": "Employee Handbook", "color": "pink"},
        {"name": "HR Policy Manual", "color": "pink"},
        {"name": "Onboarding Checklist", "color": "pink"},
        {"name": "Performance Appraisal Form", "color": "pink"},
        {"name": "Leave Policy Document", "color": "pink"},
        {"name": "Code of Conduct", "color": "pink"},
        {"name": "Exit Interview Form", "color": "pink"},
        {"name": "Training & Development Plan", "color": "pink"},
        # Legal & Compliance
        {"name": "Master Service Agreement (MSA)", "color": "blue"},
        {"name": "Non-Disclosure Agreement (NDA)", "color": "blue"},
        {"name": "Data Processing Agreement (DPA)", "color": "blue"},
        {"name": "Privacy Policy", "color": "blue"},
        {"name": "Terms of Service", "color": "blue"},
        {"name": "Compliance Audit Report", "color": "blue"},
        {"name": "Risk Assessment Report", "color": "blue"},
        {"name": "Intellectual Property Agreement", "color": "blue"},
        {"name": "Vendor Contract Template", "color": "blue"},
        {"name": "Regulatory Compliance Checklist", "color": "blue"},
        # Sales & Customer Facing
        {"name": "Sales Proposal Template", "color": "green"},
        {"name": "Sales Playbook", "color": "green"},
        {"name": "Customer Onboarding Guide", "color": "green"},
        {"name": "Service Level Agreement (SLA)", "color": "green"},
        {"name": "Pricing Strategy Document", "color": "green"},
        {"name": "Customer Case Study", "color": "green"},
        {"name": "Sales Contract", "color": "green"},
        {"name": "CRM Usage Guidelines", "color": "green"},
        {"name": "Quarterly Sales Report", "color": "green"},
        {"name": "Customer Feedback Report", "color": "green"},
        # Engineering & Operations
        {"name": "Software Requirements Specification (SRS)", "color": "orange"},
        {"name": "Technical Design Document (TDD)", "color": "orange"},
        {"name": "API Documentation", "color": "orange"},
        {"name": "Deployment Guide", "color": "orange"},
        {"name": "Release Notes", "color": "orange"},
        {"name": "System Architecture Document", "color": "orange"},
        {"name": "Incident Report", "color": "orange"},
        {"name": "Root Cause Analysis (RCA)", "color": "orange"},
        {"name": "DevOps Runbook", "color": "orange"},
        {"name": "Change Management Log", "color": "orange"},
        # Product & Design
        {"name": "Product Requirements Document (PRD)", "color": "purple"},
        {"name": "Product Roadmap", "color": "purple"},
        {"name": "Feature Specification Document", "color": "purple"},
        {"name": "UX Research Report", "color": "purple"},
        {"name": "Wireframe Documentation", "color": "purple"},
        {"name": "Design System Guide", "color": "purple"},
        {"name": "User Persona Document", "color": "purple"},
        {"name": "A/B Testing Report", "color": "purple"},
        {"name": "Product Strategy Document", "color": "purple"},
        {"name": "Competitive Analysis Report", "color": "purple"},
        # Marketing & Content
        {"name": "Marketing Strategy Plan", "color": "yellow"},
        {"name": "Content Calendar", "color": "yellow"},
        {"name": "Brand Guidelines", "color": "yellow"},
        {"name": "SEO Strategy Document", "color": "yellow"},
        {"name": "Campaign Performance Report", "color": "yellow"},
        {"name": "Social Media Strategy", "color": "yellow"},
        {"name": "Email Marketing Plan", "color": "yellow"},
        {"name": "Press Release Template", "color": "yellow"},
        {"name": "Market Research Report", "color": "yellow"},
        {"name": "Lead Generation Plan", "color": "yellow"},
        # Finance & Operations
        {"name": "Annual Budget Plan", "color": "red"},
        {"name": "Financial Statement Report", "color": "red"},
        {"name": "Expense Policy", "color": "red"},
        {"name": "Invoice Template", "color": "red"},
        {"name": "Procurement Policy", "color": "red"},
        {"name": "Revenue Forecast Report", "color": "red"},
        {"name": "Cash Flow Statement", "color": "red"},
        {"name": "Vendor Payment Policy", "color": "red"},
        {"name": "Cost Analysis Report", "color": "red"},
        {"name": "Financial Risk Assessment", "color": "red"},
        # Partnership & Alliances
        {"name": "Partnership Agreement", "color": "green"},
        {"name": "Memorandum of Understanding (MoU)", "color": "green"},
        {"name": "Channel Partner Agreement", "color": "green"},
        {"name": "Affiliate Program Agreement", "color": "green"},
        {"name": "Strategic Alliance Proposal", "color": "green"},
        {"name": "Partner Onboarding Guide", "color": "green"},
        {"name": "Joint Marketing Plan", "color": "green"},
        {"name": "Revenue Sharing Agreement", "color": "green"},
        {"name": "Partner Performance Report", "color": "green"},
        {"name": "NDA for Partners", "color": "green"},
        # IT & Internal Systems
        {"name": "IT Policy Manual", "color": "gray"},
        {"name": "Access Control Policy", "color": "gray"},
        {"name": "IT Asset Management Policy", "color": "gray"},
        {"name": "Backup & Recovery Policy", "color": "gray"},
        {"name": "Network Architecture Document", "color": "gray"},
        {"name": "IT Support SOP", "color": "gray"},
        {"name": "Disaster Recovery Plan", "color": "gray"},
        {"name": "Software License Tracking Log", "color": "gray"},
        {"name": "Internal System Audit Report", "color": "gray"},
        {"name": "Hardware Procurement Policy", "color": "gray"},
        # Platform & Infrastructure Operations
        {"name": "Infrastructure Architecture Document", "color": "blue"},
        {"name": "Cloud Deployment Guide", "color": "blue"},
        {"name": "Capacity Planning Report", "color": "blue"},
        {"name": "Infrastructure Monitoring Plan", "color": "blue"},
        {"name": "Incident Response Plan", "color": "blue"},
        {"name": "SLA for Infrastructure", "color": "blue"},
        {"name": "Configuration Management Document", "color": "blue"},
        {"name": "Uptime & Availability Report", "color": "blue"},
        {"name": "Infrastructure Security Policy", "color": "blue"},
        {"name": "Scalability Planning Document", "color": "blue"},
        # Data & Analytics
        {"name": "Data Governance Policy", "color": "brown"},
        {"name": "Data Dictionary", "color": "brown"},
        {"name": "Business Intelligence (BI) Report", "color": "brown"},
        {"name": "KPI Dashboard Documentation", "color": "brown"},
        {"name": "Data Pipeline Documentation", "color": "brown"},
        {"name": "Data Quality Report", "color": "brown"},
        {"name": "Analytics Strategy Document", "color": "brown"},
        {"name": "Predictive Model Report", "color": "brown"},
        {"name": "Data Privacy Impact Assessment", "color": "brown"},
        {"name": "Reporting Standards Guide", "color": "brown"},
        # QA & Testing
        {"name": "Test Plan Document", "color": "default"},
        {"name": "Test Case Template", "color": "default"},
        {"name": "Test Strategy Document", "color": "default"},
        {"name": "Bug Report Template", "color": "default"},
        {"name": "QA Checklist", "color": "default"},
        {"name": "Automation Test Plan", "color": "default"},
        {"name": "Regression Test Report", "color": "default"},
        {"name": "UAT Document", "color": "default"},
        {"name": "Test Coverage Report", "color": "default"},
        {"name": "Performance Testing Report", "color": "default"},
        # Security & Information Assurance
        {"name": "Information Security Policy", "color": "red"},
        {"name": "Cybersecurity Risk Assessment", "color": "red"},
        {"name": "Vulnerability Assessment Report", "color": "red"},
        {"name": "Penetration Testing Report", "color": "red"},
        {"name": "Security Audit Report", "color": "red"},
        {"name": "Data Classification Policy", "color": "red"},
        {"name": "Business Continuity Plan (BCP)", "color": "red"},
        {"name": "Security Awareness Training Material", "color": "red"},
    ]}},
    "Industry": {"select": {"options": [
        {"name": "SaaS", "color": "blue"},
        {"name": "FinTech", "color": "green"},
        {"name": "HealthTech", "color": "red"},
        {"name": "EdTech", "color": "orange"},
        {"name": "E-Commerce", "color": "purple"},
    ]}},
    "Status": {"select": {"options": [
        {"name": "✅ Published", "color": "green"},
        {"name": "📝 Draft", "color": "yellow"},
        {"name": "🔄 In Review", "color": "blue"},
        {"name": "❌ Archived", "color": "red"},
    ]}},
    "Version": {"rich_text": {}},
    "Score": {"number": {"format": "number"}},
    "Grade": {"select": {"options": [
        {"name": "A+", "color": "green"},
        {"name": "A", "color": "green"},
        {"name": "B+", "color": "blue"},
        {"name": "B", "color": "blue"},
        {"name": "C", "color": "yellow"},
        {"name": "D", "color": "red"},
    ]}},
    "Word Count": {"number": {"format": "number"}},
    "Published At": {"date": {}},
    "Company": {"rich_text": {}},
}

def setup_database(client: NotionClient, db_id: str) -> dict:
    """Add missing properties to the Notion database."""
    existing = get_db_properties(client, db_id)
    existing_lower = {k.lower(): k for k in existing.keys()}

    props_to_add = {}
    for prop_name, prop_config in REQUIRED_PROPERTIES.items():
        if prop_name.lower() not in existing_lower:
            props_to_add[prop_name] = prop_config

    if not props_to_add:
        return {"status": "ok", "message": "All properties already exist", "existing": list(existing.keys())}

    result = client.patch(f"/databases/{db_id}", {"properties": props_to_add})
    return {
        "status": "updated",
        "added": list(props_to_add.keys()),
        "existing": list(existing.keys()),
    }


# ══════════════════════════════════════════════════════════════
# MARKDOWN → NOTION BLOCKS CONVERTER
# ══════════════════════════════════════════════════════════════

DEPT_COLORS = {
    "HR & People Operations": "pink_background",
    "Legal & Compliance": "blue_background",
    "Sales & Customer Facing": "green_background",
    "Engineering & Operations": "orange_background",
    "Product & Design": "purple_background",
    "Marketing & Content": "yellow_background",
    "Finance & Operations": "red_background",
    "IT & Internal Systems": "gray_background",
    "Data & Analytics": "brown_background",
    "Security & Information Assurance": "red_background",
    "Platform & Infrastructure Operations": "blue_background",
    "Partnership & Alliances": "green_background",
    "QA & Testing": "default",
}

DEPT_EMOJI = {
    "HR & People Operations": "👥",
    "Legal & Compliance": "⚖️",
    "Sales & Customer Facing": "💼",
    "Engineering & Operations": "⚙️",
    "Product & Design": "🎨",
    "Marketing & Content": "📣",
    "Finance & Operations": "💰",
    "IT & Internal Systems": "🖥️",
    "Data & Analytics": "📊",
    "Security & Information Assurance": "🔐",
    "Platform & Infrastructure Operations": "☁️",
    "Partnership & Alliances": "🤝",
    "QA & Testing": "✅",
}


def rich_text(text: str, bold=False, italic=False, color="default") -> list:
    """Create a Notion rich_text array."""
    if not text:
        return [{"type": "text", "text": {"content": ""}}]

    # Parse inline bold (**text**) and italic (*text*)
    parts = []
    pattern = r'(\*\*.*?\*\*|\*.*?\*|`.*?`)'
    segments = re.split(pattern, text)

    for seg in segments:
        if not seg:
            continue
        annotations = {"bold": bold, "italic": italic, "code": False, "color": color}
        content = seg

        if seg.startswith("**") and seg.endswith("**"):
            content = seg[2:-2]
            annotations["bold"] = True
        elif seg.startswith("*") and seg.endswith("*"):
            content = seg[1:-1]
            annotations["italic"] = True
        elif seg.startswith("`") and seg.endswith("`"):
            content = seg[1:-1]
            annotations["code"] = True

        if content:
            parts.append({
                "type": "text",
                "text": {"content": content},
                "annotations": annotations,
            })

    return parts if parts else [{"type": "text", "text": {"content": text}}]


def heading_block(text: str, level: int, color: str = "default") -> dict:
    clean = re.sub(r'^#{1,3}\s*', '', text).strip()
    htype = f"heading_{min(level, 3)}"
    return {
        "object": "block",
        "type": htype,
        htype: {
            "rich_text": rich_text(clean),
            "color": color,
        }
    }


def paragraph_block(text: str, color: str = "default") -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": rich_text(text),
            "color": color,
        }
    }


def bullet_block(text: str) -> dict:
    clean = re.sub(r'^[-•*]\s*', '', text).strip()
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": rich_text(clean)},
    }


def numbered_block(text: str) -> dict:
    clean = re.sub(r'^\d+\.\s*', '', text).strip()
    return {
        "object": "block",
        "type": "numbered_list_item",
        "numbered_list_item": {"rich_text": rich_text(clean)},
    }


def divider_block() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def callout_block(text: str, emoji: str = "📋", color: str = "blue_background") -> dict:
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": rich_text(text),
            "icon": {"type": "emoji", "emoji": emoji},
            "color": color,
        }
    }


def quote_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "quote",
        "quote": {"rich_text": rich_text(text)},
    }


def code_block(text: str, language: str = "plain text") -> dict:
    return {
        "object": "block",
        "type": "code",
        "code": {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
            "language": language,
        }
    }


def table_of_contents_block() -> dict:
    return {"object": "block", "type": "table_of_contents", "table_of_contents": {"color": "default"}}


def markdown_to_blocks(markdown: str, dept: str = "") -> list:
    """Convert markdown document to Notion block list."""
    blocks = []
    lines = markdown.split("\n")
    i = 0
    section_count = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines (add spacing)
        if not stripped:
            i += 1
            continue

        # H1
        if stripped.startswith("# ") and not stripped.startswith("## "):
            i += 1
            continue  # Skip H1 — title is in DB property

        # H2 — main section with divider
        elif stripped.startswith("## "):
            section_count += 1
            if section_count > 1:
                blocks.append(divider_block())

            section_title = stripped[3:].strip()
            color = DEPT_COLORS.get(dept, "default")

            # Alternate heading colors for visual variety
            heading_color = [
                "blue", "purple", "pink", "orange", "green",
                "red", "brown", "gray"
            ][(section_count - 1) % 8]

            blocks.append(heading_block(f"## {section_title}", 2, heading_color))

        # H3
        elif stripped.startswith("### "):
            blocks.append(heading_block(stripped, 3))

        # Bullet
        elif stripped.startswith("- ") or stripped.startswith("• ") or stripped.startswith("* "):
            blocks.append(bullet_block(stripped))

        # Numbered list
        elif re.match(r'^\d+\.\s', stripped):
            blocks.append(numbered_block(stripped))

        # Table (skip complex tables — add as quote)
        elif stripped.startswith("|"):
            # Collect table rows
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not re.match(r'^\|[-:\s|]+\|$', lines[i].strip()):
                    table_lines.append(lines[i].strip())
                i += 1
            if table_lines:
                blocks.append(callout_block(
                    "\n".join(table_lines[:10]),
                    "📊", "gray_background"
                ))
            continue

        # Horizontal rule
        elif stripped in ("---", "===", "***"):
            blocks.append(divider_block())

        # Blockquote
        elif stripped.startswith("> "):
            blocks.append(quote_block(stripped[2:]))

        # Code block
        elif stripped.startswith("```"):
            code_lines = []
            lang = stripped[3:].strip() or "plain text"
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append(code_block("\n".join(code_lines), lang))

        # Regular paragraph
        else:
            # Detect if it looks like a key: value line
            if ":" in stripped and len(stripped) < 120:
                blocks.append(paragraph_block(stripped))
            else:
                # Wrap long paragraphs — truncate at 2000 chars per block
                while len(stripped) > 2000:
                    blocks.append(paragraph_block(stripped[:2000]))
                    stripped = stripped[2000:]
                if stripped:
                    blocks.append(paragraph_block(stripped))

        i += 1

    return blocks


# ══════════════════════════════════════════════════════════════
# HEADER BLOCK BUILDER — beautiful page header
# ══════════════════════════════════════════════════════════════

def build_header_blocks(
    document_type: str,
    department: str,
    industry: str,
    company: str,
    version: str,
    score: Optional[float],
    grade: Optional[str],
    word_count: Optional[int],
) -> list:
    emoji = DEPT_EMOJI.get(department, "📄")
    bg = DEPT_COLORS.get(department, "blue_background")

    blocks = [
        # Big callout header
        callout_block(
            f"{document_type} | {department} | {company}",
            emoji, bg
        ),
        divider_block(),

        # Metadata row
        callout_block(
            f"🏢 Company: {company}   |   🏭 Industry: {industry}   |   📁 Department: {department}",
            "ℹ️", "gray_background"
        ),
        callout_block(
            f"📌 Version: {version}   |   📅 Generated: {datetime.now().strftime('%B %d, %Y')}   |   "
            f"{'⭐ Score: ' + str(score) + '/100' if score else ''}   |   "
            f"{'🏆 Grade: ' + grade if grade else ''}   |   "
            f"{'📝 Words: ' + str(word_count) if word_count else ''}",
            "📊", "blue_background"
        ),
        divider_block(),

        # Table of contents
        {
            "object": "block",
            "type": "table_of_contents",
            "table_of_contents": {"color": "gray"}
        },
        divider_block(),
    ]
    return blocks


# ══════════════════════════════════════════════════════════════
# MAIN PUBLISH FUNCTION
# ══════════════════════════════════════════════════════════════

def publish_to_notion(
    token: str,
    db_id: str,
    document_type: str,
    department: str,
    industry: str,
    content: str,
    company: str = "Turabit",
    version: str = "1.0",
    score: Optional[float] = None,
    grade: Optional[str] = None,
    word_count: Optional[int] = None,
    existing_page_id: Optional[str] = None,
) -> dict:
    """
    Publish a document to Notion with beautiful formatting.
    Returns {"success": True, "page_id": "...", "url": "..."}
    """
    client = NotionClient(token)

    # 1. Get real DB properties
    db_props = get_db_properties(client, db_id)
    title_prop = find_title_property(db_props)

    # 2. Build page title
    page_title = f"{DEPT_EMOJI.get(department, '📄')} {document_type} — {company}"

    # 3. Build properties payload using REAL property names
    properties = {
        title_prop: {
            "title": [{"type": "text", "text": {"content": page_title}}]
        }
    }

    # Map our fields to whatever the DB calls them (case-insensitive)
    prop_lower = {k.lower(): k for k in db_props.keys()}

    def set_prop(our_name: str, value):
        real = prop_lower.get(our_name.lower())
        if not real:
            return
        ptype = db_props[real]
        if ptype == "select":
            properties[real] = {"select": {"name": str(value)}}
        elif ptype == "rich_text":
            properties[real] = {"rich_text": [{"type": "text", "text": {"content": str(value)}}]}
        elif ptype == "number":
            try:
                properties[real] = {"number": float(value)}
            except Exception:
                pass
        elif ptype == "date":
            properties[real] = {"date": {"start": datetime.now().isoformat()}}

    set_prop("Department", department)
    set_prop("Document Type", document_type)
    set_prop("Industry", industry)
    set_prop("Status", "✅ Published")
    set_prop("Version", version)
    set_prop("Company", company)

    if score is not None:
        set_prop("Score", score)
    if grade:
        set_prop("Grade", grade)
    if word_count:
        set_prop("Word Count", word_count)

    set_prop("Published At", datetime.now().isoformat())

    # 4. Convert markdown to Notion blocks (max 100 per request)
    header_blocks = build_header_blocks(
        document_type, department, industry, company,
        version, score, grade, word_count
    )
    content_blocks = markdown_to_blocks(content, department)
    all_blocks = header_blocks + content_blocks

    # Notion allows max 100 blocks per request
    first_batch = all_blocks[:95]
    remaining = all_blocks[95:]

    # 5. Create or update page
    if existing_page_id:
        # Archive old page and create fresh
        client.patch(f"/pages/{existing_page_id}", {"archived": True})

    page_body = {
        "parent": {"database_id": db_id},
        "icon": {"type": "emoji", "emoji": DEPT_EMOJI.get(department, "📄")},
        "cover": {
            "type": "external",
            "external": {"url": "https://images.unsplash.com/photo-1507925921958-8a62f3d1a50d?w=1200"}
        },
        "properties": properties,
        "children": first_batch,
    }

    result = client.post("/pages", page_body)

    if "id" not in result:
        return {
            "success": False,
            "error": result.get("message", "Unknown error"),
            "code": result.get("code", "unknown"),
            "details": result,
        }

    page_id = result["id"]
    page_url = result.get("url", f"https://notion.so/{page_id.replace('-', '')}")

    # 6. Append remaining blocks in batches of 95
    for batch_start in range(0, len(remaining), 95):
        batch = remaining[batch_start:batch_start + 95]
        if batch:
            client.patch(f"/blocks/{page_id}/children", {"children": batch})

    return {
        "success": True,
        "page_id": page_id,
        "url": page_url,
        "title": page_title,
        "blocks_created": len(all_blocks),
    }

# ══════════════════════════════════════════════════════════════
# TEST TOKEN
# ══════════════════════════════════════════════════════════════

def test_token(token: str) -> dict:
    client = NotionClient(token)
    result = client.get("/users/me")
    if "id" in result:
        return {
            "valid": True,
            "user": result.get("name", "Unknown"),
            "type": result.get("type", "unknown"),
        }
    return {"valid": False, "error": result.get("message", "Invalid token")}


def test_database_access(token: str, db_id: str) -> dict:
    client = NotionClient(token)
    result = client.get(f"/databases/{db_id}")
    if "id" in result:
        props = result.get("properties", {})
        return {
            "valid": True,
            "title": result.get("title", [{}])[0].get("plain_text", "Untitled"),
            "properties": {k: v["type"] for k, v in props.items()},
            "property_count": len(props),
        }
    return {"valid": False, "error": result.get("message", "Cannot access database")}


def get_user_databases(token: str) -> list:
    client = NotionClient(token)
    result = client.post("/search", {
        "filter": {"value": "database", "property": "object"},
        "page_size": 20,
    })
    dbs = []
    for db in result.get("results", []):
        title_arr = db.get("title", [])
        title = title_arr[0].get("plain_text", "Untitled") if title_arr else "Untitled"
        dbs.append({
            "id": db["id"],
            "title": title,
            "url": db.get("url", ""),
        })
    return dbs

def check_notion_page_exists(page_id: str, token: str) -> bool:
    """Check if Notion page still exists (not trashed)."""
    try:
        resp = requests.get(
            f"{NOTION_API_URL}/pages/{page_id}",
            headers=notion_headers(token),
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Trashed pages return archived=True
            return not data.get("archived", False)
        return False
    except Exception:
        return False

