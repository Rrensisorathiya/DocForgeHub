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

NOTION_VERSION = "2022-06-28"


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

#----------------------------------------------------------------------

#  """
# Notion Integration Service  —  DocForgeHub
# ==========================================
# Publishes any DocForgeHub markdown document to Notion exactly as-is:
#   - All headings (H1 / H2 / H3)
#   - All paragraphs with **bold** and `code` inline
#   - All bullet lists and numbered lists
#   - All tables (two-step Notion API)
#   - Dividers / horizontal rules
#   - Blockquotes

# Database properties written on every publish:
#   Name (title), type, version, created_by, word_count
#   + any extra columns that exist: industry, department, tags, status

# Rate-limit safe: exponential backoff + jitter on 429 / 500 / 503
# """

# from __future__ import annotations

# import html as _html
# import logging
# import random
# import re
# import time
# from datetime import datetime, timezone
# from typing import Any, Optional

# from notion_client import Client
# from notion_client.errors import APIResponseError

# log = logging.getLogger(__name__)

# # ── Notion hard limits ────────────────────────────────────────────────────────
# _MAX_TEXT   = 1990   # chars per rich-text chunk (limit is 2000)
# _MAX_BATCH  = 90     # blocks per append call    (limit is 100)

# # ── Retry config ──────────────────────────────────────────────────────────────
# _RETRIES    = 6
# _BACKOFF    = 1.5    # seconds (doubles each retry)
# _BACKOFF_CAP = 60.0


# # ═════════════════════════════════════════════════════════════════════════════
# # 1.  RATE-LIMIT WRAPPER
# # ═════════════════════════════════════════════════════════════════════════════

# def _call(fn, *args, **kwargs):
#     delay = _BACKOFF
#     for attempt in range(_RETRIES + 1):
#         try:
#             return fn(*args, **kwargs)
#         except APIResponseError as e:
#             if e.status in (429, 500, 503) and attempt < _RETRIES:
#                 wait = min(delay + random.uniform(0, delay * 0.25), _BACKOFF_CAP)
#                 log.warning("Notion %s – retry %d/%d in %.1fs", e.status, attempt+1, _RETRIES, wait)
#                 time.sleep(wait)
#                 delay = min(delay * 2, _BACKOFF_CAP)
#             else:
#                 raise


# # ═════════════════════════════════════════════════════════════════════════════
# # 2.  DOCUMENT PRE-PROCESSING
# # ═════════════════════════════════════════════════════════════════════════════

# def _strip_frontmatter(raw: str) -> tuple[dict, str]:
#     """
#     Remove the YAML front-matter block DocForgeHub prepends:
#         ---
#         Type       : Employment Contract
#         Department : HR & People Operations
#         Industry   : SaaS
#         Date       : 2026-03-12 12:16
#         ---
#     Returns (meta_dict, content_without_frontmatter).
#     """
#     m = re.match(r"^\s*---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
#     if not m:
#         return {}, raw
#     meta = {}
#     for line in m.group(1).splitlines():
#         if ":" in line:
#             k, _, v = line.partition(":")
#             meta[k.strip().lower()] = v.strip()
#     return meta, raw[m.end():]


# def _clean_h1(content: str) -> tuple[str, str]:
#     """
#     DocForgeHub H1 looks like:
#         # Employment Contract | Employment Contract | HR & People | Version 1.0 | ...
#     Extract first segment as page title; replace full H1 with clean version.
#     Returns (page_title, cleaned_content).
#     """
#     m = re.match(r"^#\s+(.+)$", content.lstrip(), re.MULTILINE)
#     if not m:
#         return "Untitled", content
#     raw_h1    = m.group(1)
#     title     = raw_h1.split("|")[0].strip()
#     cleaned   = content.replace(m.group(0), f"# {title}", 1)
#     return title, cleaned


# def preprocess(raw: str, title_override: str = "") -> tuple[str, str, dict]:
#     """
#     Full pipeline: strip front-matter → clean H1 → return (title, content, meta).
#     """
#     meta, content = _strip_frontmatter(raw)
#     auto_title, content = _clean_h1(content)
#     title = title_override.strip() or auto_title
#     return title, content, meta


# # ═════════════════════════════════════════════════════════════════════════════
# # 3.  RICH-TEXT BUILDER  (handles **bold** and `code`)
# # ═════════════════════════════════════════════════════════════════════════════

# def _rt(text: str, bold=False, code=False) -> dict:
#     obj: dict[str, Any] = {"type": "text", "text": {"content": text[:_MAX_TEXT]}}
#     ann = {}
#     if bold: ann["bold"] = True
#     if code: ann["code"] = True
#     if ann:  obj["annotations"] = ann
#     return obj


# def _rt_list(text: str) -> list[dict]:
#     """Parse inline **bold** / `code` spans and return rich-text array."""
#     if not text:
#         return [_rt("")]
#     out   = []
#     pos   = 0
#     pat   = re.compile(r"(`[^`\n]+`|\*\*[^*\n]+\*\*)")
#     for m in pat.finditer(text):
#         if m.start() > pos:
#             for chunk in _chunks(text[pos:m.start()]):
#                 out.append(_rt(chunk))
#         tok = m.group(0)
#         if tok.startswith("`"):
#             for chunk in _chunks(tok[1:-1]):
#                 out.append(_rt(chunk, code=True))
#         else:
#             for chunk in _chunks(tok[2:-2]):
#                 out.append(_rt(chunk, bold=True))
#         pos = m.end()
#     if pos < len(text):
#         for chunk in _chunks(text[pos:]):
#             out.append(_rt(chunk))
#     return out or [_rt("")]


# def _chunks(s: str):
#     for i in range(0, max(len(s), 1), _MAX_TEXT):
#         yield s[i:i+_MAX_TEXT]


# # ═════════════════════════════════════════════════════════════════════════════
# # 4.  BLOCK BUILDERS
# # ═════════════════════════════════════════════════════════════════════════════

# def _heading(level: int, text: str) -> dict:
#     t = {1: "heading_1", 2: "heading_2", 3: "heading_3"}[min(level, 3)]
#     return {"object": "block", "type": t, t: {"rich_text": _rt_list(text)}}

# def _para(text: str) -> dict:
#     return {"object": "block", "type": "paragraph",
#             "paragraph": {"rich_text": _rt_list(text)}}

# def _bullet(text: str) -> dict:
#     return {"object": "block", "type": "bulleted_list_item",
#             "bulleted_list_item": {"rich_text": _rt_list(text)}}

# def _numbered(text: str) -> dict:
#     return {"object": "block", "type": "numbered_list_item",
#             "numbered_list_item": {"rich_text": _rt_list(text)}}

# def _quote(text: str) -> dict:
#     return {"object": "block", "type": "quote",
#             "quote": {"rich_text": _rt_list(text)}}

# def _code_block(text: str, lang: str = "plain text") -> dict:
#     return {"object": "block", "type": "code",
#             "code": {"rich_text": [_rt(text[:_MAX_TEXT])], "language": lang}}

# def _divider() -> dict:
#     return {"object": "block", "type": "divider", "divider": {}}


# # ═════════════════════════════════════════════════════════════════════════════
# # 5.  TABLE PARSING  (markdown → Notion two-step)
# # ═════════════════════════════════════════════════════════════════════════════

# class _Table:
#     """Pending table — appended via two-step Notion API."""
#     __slots__ = ("cols", "rows")
#     def __init__(self, cols: int, rows: list[list[str]]):
#         self.cols = cols
#         self.rows = rows


# def _parse_md_table(lines: list[str]) -> Optional[_Table]:
#     rows = []
#     for ln in lines:
#         ln = ln.strip()
#         if not ln.startswith("|"):
#             break
#         cells = [c.strip() for c in ln.strip("|").split("|")]
#         # skip separator row (---|---|---)
#         if all(re.match(r"^:?-+:?$", c) for c in cells if c):
#             continue
#         rows.append(cells)
#     if not rows:
#         return None
#     cols = max(len(r) for r in rows)
#     rows = [r + [""] * (cols - len(r)) for r in rows]
#     return _Table(cols, rows)


# def _html_to_md_table(html_str: str) -> str:
#     """Convert <table> HTML to markdown (fallback for HTML tables in docs)."""
#     html_str = re.sub(r"<!--.*?-->", "", html_str, flags=re.DOTALL)
#     def cell_text(c):
#         return _html.unescape(re.sub(r"<[^>]+>", "", c)).strip().replace("|", "\\|").replace("\n", " ")
#     rows = []
#     for row in re.finditer(r"<tr[^>]*>(.*?)</tr>", html_str, re.DOTALL | re.I):
#         cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row.group(1), re.DOTALL | re.I)
#         if cells:
#             rows.append([cell_text(c) for c in cells])
#     if not rows:
#         return html_str
#     cols = max(len(r) for r in rows)
#     rows = [r + [""]*(cols-len(r)) for r in rows]
#     lines = ["| "+" | ".join(rows[0])+" |",
#              "| "+" | ".join(["---"]*cols)+" |"]
#     lines += ["| "+" | ".join(r)+" |" for r in rows[1:]]
#     return "\n".join(lines)


# # ═════════════════════════════════════════════════════════════════════════════
# # 6.  MARKDOWN → BLOCK LIST PARSER
# # ═════════════════════════════════════════════════════════════════════════════

# def _parse(content: str) -> list:
#     """Convert markdown to list of block dicts and _Table sentinels."""

#     # Convert any HTML tables first
#     content = re.sub(r"<table[^>]*>.*?</table>",
#                      lambda m: _html_to_md_table(m.group(0)),
#                      content, flags=re.DOTALL | re.I)

#     lines  = content.splitlines()
#     blocks = []
#     i      = 0
#     in_code     = False
#     code_lines  = []
#     code_lang   = "plain text"

#     while i < len(lines):
#         raw     = lines[i]
#         stripped = raw.strip()

#         # ── fenced code block ──────────────────────────────────────────
#         if stripped.startswith("```"):
#             if not in_code:
#                 in_code    = True
#                 code_lang  = stripped[3:].strip() or "plain text"
#                 code_lines = []
#             else:
#                 in_code   = False
#                 code_text = "\n".join(code_lines)
#                 for j in range(0, max(len(code_text), 1), _MAX_TEXT):
#                     blocks.append(_code_block(code_text[j:j+_MAX_TEXT], code_lang))
#                 code_lines = []
#             i += 1
#             continue

#         if in_code:
#             code_lines.append(raw)
#             i += 1
#             continue

#         # ── blank line ─────────────────────────────────────────────────
#         if not stripped:
#             i += 1
#             continue

#         # ── divider  --- / *** / ___ ───────────────────────────────────
#         if re.match(r"^[-*_]{3,}$", stripped):
#             blocks.append(_divider())
#             i += 1
#             continue

#         # ── heading  # ## ### ─────────────────────────────────────────
#         m = re.match(r"^(#{1,3})\s+(.*)", stripped)
#         if m:
#             blocks.append(_heading(len(m.group(1)), m.group(2).strip()))
#             i += 1
#             continue

#         # ── markdown table  | col | col | ─────────────────────────────
#         if stripped.startswith("|") and "|" in stripped[1:]:
#             tbl_lines = []
#             while i < len(lines) and lines[i].strip().startswith("|"):
#                 tbl_lines.append(lines[i])
#                 i += 1
#             t = _parse_md_table(tbl_lines)
#             if t:
#                 blocks.append(t)
#             else:
#                 blocks.append(_code_block("\n".join(tbl_lines)))
#             continue

#         # ── blockquote  > ─────────────────────────────────────────────
#         if stripped.startswith(">"):
#             q_lines = [re.sub(r"^>\s*", "", stripped)]
#             i += 1
#             while i < len(lines) and lines[i].strip().startswith(">"):
#                 q_lines.append(re.sub(r"^>\s*", "", lines[i].strip()))
#                 i += 1
#             blocks.append(_quote(" ".join(q_lines)))
#             continue

#         # ── bullet  * - + ─────────────────────────────────────────────
#         m = re.match(r"^[*\-+]\s+(.*)", stripped)
#         if m:
#             blocks.append(_bullet(m.group(1)))
#             i += 1
#             continue

#         # ── numbered list  1. 2) ──────────────────────────────────────
#         m = re.match(r"^\d+[.)]\s+(.*)", stripped)
#         if m:
#             blocks.append(_numbered(m.group(1)))
#             i += 1
#             continue

#         # ── paragraph (collect consecutive lines) ─────────────────────
#         para_lines = []
#         while i < len(lines):
#             l = lines[i].strip()
#             if not l:
#                 break
#             if (l.startswith("#") or l.startswith("|") or l.startswith(">")
#                     or re.match(r"^[*\-+]\s", l) or re.match(r"^\d+[.)]\s", l)
#                     or re.match(r"^[-*_]{3,}$", l) or l.startswith("```")):
#                 break
#             para_lines.append(l)
#             i += 1

#         if para_lines:
#             text = " ".join(para_lines)
#             for j in range(0, max(len(text), 1), _MAX_TEXT):
#                 blocks.append(_para(text[j:j+_MAX_TEXT]))

#     return blocks


# # ═════════════════════════════════════════════════════════════════════════════
# # 7.  APPEND BLOCKS TO NOTION PAGE  (handles tables via two-step API)
# # ═════════════════════════════════════════════════════════════════════════════

# def _flush(notion: Client, page_id: str, batch: list[dict]) -> None:
#     if not batch:
#         return
#     for i in range(0, len(batch), _MAX_BATCH):
#         _call(notion.blocks.children.append,
#               block_id=page_id, children=batch[i:i+_MAX_BATCH])


# def _append_table(notion: Client, page_id: str, t: _Table) -> None:
#     """Two-step: create shell → append rows."""
#     shell = {
#         "object": "block", "type": "table",
#         "table": {
#             "table_width":      t.cols,
#             "has_column_header": True,
#             "has_row_header":    False,
#         }
#     }
#     resp  = _call(notion.blocks.children.append, block_id=page_id, children=[shell])
#     tid   = resp["results"][0]["id"]
#     rows  = [{"object": "block", "type": "table_row",
#                "table_row": {"cells": [_rt_list(c) for c in row]}}
#              for row in t.rows]
#     for i in range(0, len(rows), _MAX_BATCH):
#         _call(notion.blocks.children.append,
#               block_id=tid, children=rows[i:i+_MAX_BATCH])


# def _append_all(notion: Client, page_id: str, blocks: list) -> int:
#     """Append all blocks; flush regular batch before each table."""
#     buf   = []
#     count = 0
#     for b in blocks:
#         if isinstance(b, _Table):
#             _flush(notion, page_id, buf)
#             count += len(buf)
#             buf = []
#             _append_table(notion, page_id, b)
#             count += 1
#         else:
#             buf.append(b)
#             if len(buf) >= _MAX_BATCH:
#                 _flush(notion, page_id, buf)
#                 count += len(buf)
#                 buf = []
#     _flush(notion, page_id, buf)
#     count += len(buf)
#     return count


# # ═════════════════════════════════════════════════════════════════════════════
# # 8.  DATABASE SETUP  (create missing columns, never touch title column)
# # ═════════════════════════════════════════════════════════════════════════════

# # These are the columns we will CREATE if missing.
# # All lowercase to match your DocForgeHub DB screenshot.
# _COLUMNS: dict[str, dict] = {
#     "type":        {"select": {}},
#     "version":     {"rich_text": {}},
#     "created_by":  {"rich_text": {}},
#     "word_count":  {"number": {"format": "number"}},
#     "industry":    {"select": {}},
#     "department":  {"rich_text": {}},
#     "tags":        {"multi_select": {}},
#     "status":      {"select": {}},
# }


# def _setup_db(notion: Client, db_id: str) -> str:
#     """
#     1. Retrieve DB properties.
#     2. Find the title-type column name (could be "Title", "Name", anything).
#     3. Create any missing columns from _COLUMNS (skipping title column).
#     Returns the title column name.
#     """
#     db    = _call(notion.databases.retrieve, database_id=db_id)
#     props = db.get("properties", {})

#     # Find title column name dynamically
#     title_col = "Name"  # fallback
#     for name, schema in props.items():
#         if schema.get("type") == "title":
#             title_col = name
#             log.info("Title column detected: '%s'", title_col)
#             break

#     # Build set of existing column names (case-insensitive)
#     existing = {k.lower() for k in props}

#     # Create missing columns
#     to_create = {k: v for k, v in _COLUMNS.items() if k.lower() not in existing}
#     if to_create:
#         _call(notion.databases.update, database_id=db_id, properties=to_create)
#         log.info("Created %d missing columns: %s", len(to_create), list(to_create))

#     return title_col


# # ═════════════════════════════════════════════════════════════════════════════
# # 9.  BUILD PAGE PROPERTIES
# # ═════════════════════════════════════════════════════════════════════════════

# def _build_props(
#     title_col:  str,
#     title:      str,
#     doc_type:   str,
#     industry:   str,
#     department: str,
#     version:    str,
#     created_by: str,
#     tags:       list[str],
#     status:     str,
#     word_count: int,
# ) -> dict:
#     props: dict[str, Any] = {
#         title_col: {"title": [{"type": "text", "text": {"content": title[:255]}}]},
#     }
#     def _s(col, val):
#         if val: props[col] = {"select": {"name": val[:100]}}
#     def _r(col, val):
#         if val: props[col] = {"rich_text": [_rt(val[:_MAX_TEXT])]}
#     def _n(col, val):
#         props[col] = {"number": val}
#     def _m(col, vals):
#         if vals: props[col] = {"multi_select": [{"name": v[:100]} for v in vals[:20]]}

#     _s("type",       doc_type)
#     _s("industry",   industry)
#     _s("status",     status or "Active")
#     _r("version",    version)
#     _r("created_by", created_by)
#     _r("department", department)
#     _n("word_count", word_count)
#     _m("tags",       tags)

#     return props


# # ═════════════════════════════════════════════════════════════════════════════
# # 10.  PUBLIC API
# # ═════════════════════════════════════════════════════════════════════════════

# def test_notion_connection(token: str, database_id: str) -> dict:
#     """Verify token + database access. Returns success/error dict."""
#     try:
#         notion = Client(auth=token)
#         db     = _call(notion.databases.retrieve, database_id=database_id)
#         name   = "".join(p.get("plain_text","") for p in db.get("title",[])) or "Untitled"
#         return {"success": True, "database_title": name,
#                 "message": f"Connected to '{name}'"}
#     except APIResponseError as e:
#         msgs = {
#             401: "Invalid token — check your secret_xxxx key.",
#             403: "Integration has no access — share the DB with your integration.",
#             404: "Database not found — verify the database_id.",
#         }
#         return {"success": False, "error": msgs.get(e.status, f"Notion error {e.status}: {e.message}")}
#     except Exception as e:
#         return {"success": False, "error": str(e)}


# def publish_document_to_notion(
#     token:       str,
#     database_id: str,
#     title:       str,
#     content:     str,
#     doc_type:    str  = "",
#     industry:    str  = "",
#     version:     str  = "",
#     tags:        Optional[list[str]] = None,
#     created_by:  str  = "",
#     status:      str  = "Active",
#     source_template_id: str = "",
#     source_prompts:     str = "",
#     skip_quality_gates: bool = False,
# ) -> dict:
#     """
#     Full publish pipeline:
#       1. Strip front-matter + clean H1 title
#       2. Detect title column name from DB
#       3. Auto-create missing DB columns
#       4. Parse markdown → Notion blocks (headings, bullets, tables, etc.)
#       5. Create page with metadata
#       6. Append all blocks (tables via two-step API)
#     """
#     try:
#         notion = Client(auth=token)

#         # ── Step 1: Pre-process content ───────────────────────────────
#         clean_title, clean_content, meta = preprocess(content, title)

#         # Fill metadata from front-matter if not supplied by caller
#         final_type   = doc_type   or meta.get("type", "")
#         final_ind    = industry   or meta.get("industry", "")
#         final_dept   = meta.get("department", "")
#         final_ver    = version    or "1.0"
#         final_tags   = tags or list(filter(None, [final_type, final_dept]))
#         final_by     = created_by or "DocForgeHub"

#         log.info("Publishing '%s' | type=%s | %d chars",
#                  clean_title, final_type, len(clean_content))

#         # ── Step 2+3: DB setup — detect title col, create missing cols ─
#         title_col = _setup_db(notion, database_id)

#         # ── Step 4: Parse markdown → blocks ───────────────────────────
#         blocks     = _parse(clean_content)
#         word_count = len(clean_content.split())
#         tables     = sum(1 for b in blocks if isinstance(b, _Table))
#         log.info("Parsed: %d blocks (%d tables)", len(blocks), tables)

#         # ── Step 5: Create Notion page with properties ────────────────
#         props = _build_props(
#             title_col  = title_col,
#             title      = clean_title,
#             doc_type   = final_type,
#             industry   = final_ind,
#             department = final_dept,
#             version    = final_ver,
#             created_by = final_by,
#             tags       = final_tags,
#             status     = status,
#             word_count = word_count,
#         )

#         page  = _call(notion.pages.create,
#                       parent={"database_id": database_id},
#                       properties=props)
#         pid   = page["id"]
#         url   = page.get("url", f"https://notion.so/{pid.replace('-','')}")
#         log.info("Page created: %s", url)

#         # ── Step 6: Append all blocks ─────────────────────────────────
#         total = _append_all(notion, pid, blocks)
#         log.info("Done — %d blocks appended to %s", total, url)

#         return {
#             "success":      True,
#             "page_id":      pid,
#             "page_url":     url,
#             "title":        clean_title,
#             "doc_type":     final_type,
#             "industry":     final_ind,
#             "department":   final_dept,
#             "version":      final_ver,
#             "word_count":   word_count,
#             "total_blocks": len(blocks),
#             "tables":       tables,
#         }

#     except APIResponseError as e:
#         log.error("Notion API error: %s", e.message)
#         return {"success": False, "error": f"Notion API error ({e.status}): {e.message}"}
#     except Exception as e:
#         log.exception("Unexpected error")
#         return {"success": False, "error": str(e)}


# def list_notion_pages(token: str, database_id: str, limit: int = 20) -> dict:
#     """List recently published pages, sorted newest first."""
#     try:
#         notion = Client(auth=token)
#         resp   = _call(notion.databases.query,
#                        database_id=database_id,
#                        page_size=min(limit, 100),
#                        sorts=[{"timestamp": "created_time", "direction": "descending"}])
#         pages  = []
#         for p in resp.get("results", []):
#             pr = p.get("properties", {})

#             def title_val() -> str:
#                 for v in pr.values():
#                     if v.get("type") == "title":
#                         return "".join(x.get("plain_text","") for x in v.get("title",[]))
#                 return ""

#             def sel(k):
#                 s = pr.get(k,{}).get("select"); return s["name"] if s else ""

#             def txt(k):
#                 parts = pr.get(k,{}).get("rich_text",[])
#                 return "".join(x.get("plain_text","") for x in parts)

#             def multi(k):
#                 return [x["name"] for x in pr.get(k,{}).get("multi_select",[])]

#             pages.append({
#                 "page_id":    p["id"],
#                 "page_url":   p.get("url",""),
#                 "title":      title_val(),
#                 "type":       sel("type"),
#                 "industry":   sel("industry"),
#                 "status":     sel("status"),
#                 "version":    txt("version"),
#                 "created_by": txt("created_by"),
#                 "department": txt("department"),
#                 "tags":       multi("tags"),
#                 "word_count": pr.get("word_count",{}).get("number"),
#                 "created_time": p.get("created_time",""),
#             })
#         return {"success": True, "pages": pages, "total": len(pages)}

#     except APIResponseError as e:
#         return {"success": False, "error": f"Notion API error ({e.status}): {e.message}"}
#     except Exception as e:
#         return {"success": False, "error": str(e)}


# def update_page_status(token: str, page_id: str, status: str) -> dict:
#     """Update the status column of an existing Notion page."""
#     try:
#         notion = Client(auth=token)
#         _call(notion.pages.update, page_id=page_id,
#               properties={"status": {"select": {"name": status[:100]}}})
#         return {"success": True, "page_id": page_id, "status": status}
#     except APIResponseError as e:
#         return {"success": False, "error": f"Notion API error ({e.status}): {e.message}"}
#     except Exception as e:
#         return {"success": False, "error": str(e)}

#--------------------------------------------------------------------------------------

# """
# Notion Integration Service
# ──────────────────────────
# Features:
#   - Publishes FULL documents — every section, every table, every paragraph
#   - Flat readable pages: headings + content directly on page, no toggles
#   - Full markdown TABLE support via Notion's two-step API:
#       Step 1: append empty table shell → get block_id
#       Step 2: append table_row children to that block_id
#   - HTML table fallback: converts <table> HTML to markdown before parsing
#   - Rate-limit aware with exponential backoff + jitter
#   - Smart block parser: h1/h2/h3, bullets, numbered, quotes, dividers, tables, paragraphs
#   - Quality gates: minimum sections, policy doc scope/definitions/exceptions checks
#   - Full metadata: type, industry, version, tags, created_by, status, source
#   - Auto-creates missing Notion DB properties on first publish
#   - Pagination: long docs split into ≤ SECTION_BLOCK_LIMIT-block batches
# """

# from __future__ import annotations

# import html
# import logging
# import math
# import random
# import re
# import time
# from datetime import datetime, timezone
# from typing import Any, Optional

# from notion_client import Client
# from notion_client.errors import APIResponseError

# logger = logging.getLogger(__name__)


# # ─────────────────────────────────────────────────────────────────────────────
# # Constants
# # ─────────────────────────────────────────────────────────────────────────────

# MAX_BLOCK_CHARS     = 2000   # Notion hard limit per rich-text segment
# MAX_TEXT_BLOCK      = 1990   # Leave 10-char safety margin
# MAX_CHILDREN_BATCH  = 100    # Notion hard limit per append_block_children call
# SECTION_BLOCK_LIMIT = 80     # Blocks per batch (conservative, avoids timeout)
# RATE_LIMIT_RETRIES  = 6
# RATE_LIMIT_BASE     = 1.5    # seconds — base backoff
# RATE_LIMIT_CAP      = 60.0   # seconds — max backoff

# # Quality gates
# MIN_SECTIONS            = 3
# POLICY_REQUIRED_TERMS   = ["scope", "definition", "exception"]   # at least 2 of 3
# CONTENT_MIN_CHARS       = 300

# # Notion property type constants
# PROP_TITLE     = "title"
# PROP_RICH_TEXT = "rich_text"
# PROP_SELECT    = "select"
# PROP_MULTI     = "multi_select"
# PROP_DATE      = "date"
# PROP_PEOPLE    = "people"
# PROP_NUMBER    = "number"
# PROP_CHECKBOX  = "checkbox"
# PROP_URL       = "url"


# # ─────────────────────────────────────────────────────────────────────────────
# # Client + Rate-limit wrapper
# # ─────────────────────────────────────────────────────────────────────────────

# def _get_client(token: str) -> Client:
#     return Client(auth=token)


# def _call(fn, *args, **kwargs):
#     """
#     Call a Notion SDK function with exponential backoff + jitter on 429/500/502.
#     Raises on unrecoverable errors.
#     """
#     delay = RATE_LIMIT_BASE
#     for attempt in range(RATE_LIMIT_RETRIES + 1):
#         try:
#             return fn(*args, **kwargs)
#         except APIResponseError as exc:
#             retriable = exc.status in (429, 500, 502, 503)
#             if retriable and attempt < RATE_LIMIT_RETRIES:
#                 jitter = random.uniform(0, delay * 0.3)
#                 wait   = min(delay + jitter, RATE_LIMIT_CAP)
#                 logger.warning(
#                     "Notion API %s (status=%s). Retry %d/%d in %.1fs…",
#                     exc.code, exc.status, attempt + 1, RATE_LIMIT_RETRIES, wait,
#                 )
#                 time.sleep(wait)
#                 delay = min(delay * 2, RATE_LIMIT_CAP)
#             else:
#                 logger.error("Notion API error (status=%s): %s", exc.status, exc.message)
#                 raise


# # ─────────────────────────────────────────────────────────────────────────────
# # Quality Gates
# # ─────────────────────────────────────────────────────────────────────────────

# class QualityGateError(ValueError):
#     """Raised when a document fails quality checks before publishing."""


# def run_quality_gates(
#     content: str,
#     doc_type: Optional[str] = None,
#     title: Optional[str] = None,
# ) -> None:
#     """
#     Validate document quality before publishing.
#     Raises QualityGateError with a descriptive message on failure.
#     """
#     if not content or len(content.strip()) < CONTENT_MIN_CHARS:
#         raise QualityGateError(
#             f"Document content is too short ({len(content.strip())} chars). "
#             f"Minimum required: {CONTENT_MIN_CHARS} chars."
#         )

#     # Count headings as section markers
#     heading_pattern = re.compile(r"^#{1,3}\s+\S", re.MULTILINE)
#     sections = heading_pattern.findall(content)
#     if len(sections) < MIN_SECTIONS:
#         raise QualityGateError(
#             f"Document has only {len(sections)} section heading(s). "
#             f"Minimum required: {MIN_SECTIONS}. "
#             "Add more ## Section headings to structure your document."
#         )

#     # Policy-specific checks
#     is_policy = doc_type and any(
#         kw in (doc_type or "").lower()
#         for kw in ("policy", "handbook", "compliance", "procedure", "standard", "guideline")
#     )
#     if is_policy:
#         lower = content.lower()
#         found = [term for term in POLICY_REQUIRED_TERMS if term in lower]
#         if len(found) < 2:
#             missing = [t for t in POLICY_REQUIRED_TERMS if t not in found]
#             raise QualityGateError(
#                 f"Policy document '{title}' is missing required sections: {missing}. "
#                 "Policy documents must address scope, definitions, and exceptions."
#             )

#     logger.info(
#         "Quality gates passed — %d chars, %d sections%s.",
#         len(content),
#         len(sections),
#         f", policy checks OK" if is_policy else "",
#     )


# # ─────────────────────────────────────────────────────────────────────────────
# # HTML → Markdown table converter
# # ─────────────────────────────────────────────────────────────────────────────

# def _html_table_to_markdown(html_str: str) -> str:
#     """Convert an HTML <table> block to a GitHub-Flavored Markdown table."""
#     html_str = re.sub(r"<!--.*?-->", "", html_str, flags=re.DOTALL)

#     def _cell_text(cell_html: str) -> str:
#         text = re.sub(r"<[^>]+>", "", cell_html)
#         return html.unescape(text).strip().replace("|", "\\|").replace("\n", " ")

#     rows: list[list[str]] = []
#     for row_match in re.finditer(r"<tr[^>]*>(.*?)</tr>", html_str, re.DOTALL | re.IGNORECASE):
#         cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_match.group(1), re.DOTALL | re.IGNORECASE)
#         if cells:
#             rows.append([_cell_text(c) for c in cells])

#     if not rows:
#         return ""

#     col_count = max(len(r) for r in rows)
#     # Pad short rows
#     padded = [r + [""] * (col_count - len(r)) for r in rows]

#     header = padded[0]
#     sep    = ["---"] * col_count
#     body   = padded[1:]

#     lines = [
#         "| " + " | ".join(header) + " |",
#         "| " + " | ".join(sep)    + " |",
#         *["| " + " | ".join(row) + " |" for row in body],
#     ]
#     return "\n".join(lines)


# def _preprocess_html_tables(content: str) -> str:
#     """Replace all HTML tables in content with markdown equivalents."""
#     def _replacer(m: re.Match) -> str:
#         md = _html_table_to_markdown(m.group(0))
#         return md if md else m.group(0)

#     return re.sub(r"<table[^>]*>.*?</table>", _replacer, content, flags=re.DOTALL | re.IGNORECASE)


# # ─────────────────────────────────────────────────────────────────────────────
# # Rich-text helpers
# # ─────────────────────────────────────────────────────────────────────────────

# def _rich_text(text: str, bold: bool = False, code: bool = False) -> dict:
#     chunk = text[:MAX_TEXT_BLOCK]
#     annotations: dict[str, Any] = {}
#     if bold:
#         annotations["bold"] = True
#     if code:
#         annotations["code"] = True
#     obj: dict[str, Any] = {"type": "text", "text": {"content": chunk}}
#     if annotations:
#         obj["annotations"] = annotations
#     return obj


# def _rich_text_list(text: str) -> list[dict]:
#     """
#     Split long text into ≤ MAX_TEXT_BLOCK chunks.
#     Inline **bold** and `code` spans are preserved.
#     """
#     if not text:
#         return [_rich_text("")]

#     # Parse inline markdown bold and code
#     segments: list[dict] = []
#     pattern = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*)")
#     pos = 0
#     for m in pattern.finditer(text):
#         if m.start() > pos:
#             segments.append(("plain", text[pos:m.start()]))
#         token = m.group(0)
#         if token.startswith("`"):
#             segments.append(("code", token[1:-1]))
#         else:
#             segments.append(("bold", token[2:-2]))
#         pos = m.end()
#     if pos < len(text):
#         segments.append(("plain", text[pos:]))

#     result: list[dict] = []
#     for kind, raw in segments:
#         # Chunk long plain/bold/code segments
#         for i in range(0, max(len(raw), 1), MAX_TEXT_BLOCK):
#             chunk = raw[i:i + MAX_TEXT_BLOCK]
#             if kind == "bold":
#                 result.append(_rich_text(chunk, bold=True))
#             elif kind == "code":
#                 result.append(_rich_text(chunk, code=True))
#             else:
#                 result.append(_rich_text(chunk))
#     return result or [_rich_text("")]


# # ─────────────────────────────────────────────────────────────────────────────
# # Block builders
# # ─────────────────────────────────────────────────────────────────────────────

# def _heading_block(level: int, text: str) -> dict:
#     key = {1: "heading_1", 2: "heading_2", 3: "heading_3"}.get(level, "heading_3")
#     return {
#         "object": "block",
#         "type": key,
#         key: {"rich_text": _rich_text_list(text)},
#     }


# def _paragraph_block(text: str) -> dict:
#     return {
#         "object": "block",
#         "type": "paragraph",
#         "paragraph": {"rich_text": _rich_text_list(text)},
#     }


# def _bullet_block(text: str) -> dict:
#     return {
#         "object": "block",
#         "type": "bulleted_list_item",
#         "bulleted_list_item": {"rich_text": _rich_text_list(text)},
#     }


# def _numbered_block(text: str) -> dict:
#     return {
#         "object": "block",
#         "type": "numbered_list_item",
#         "numbered_list_item": {"rich_text": _rich_text_list(text)},
#     }


# def _quote_block(text: str) -> dict:
#     return {
#         "object": "block",
#         "type": "quote",
#         "quote": {"rich_text": _rich_text_list(text)},
#     }


# def _code_block(text: str, language: str = "plain text") -> dict:
#     # Notion code blocks have a 2000-char limit too
#     return {
#         "object": "block",
#         "type": "code",
#         "code": {
#             "rich_text": [_rich_text(text[:MAX_TEXT_BLOCK])],
#             "language": language,
#         },
#     }


# def _divider_block() -> dict:
#     return {"object": "block", "type": "divider", "divider": {}}


# def _callout_block(text: str, emoji: str = "📌") -> dict:
#     return {
#         "object": "block",
#         "type": "callout",
#         "callout": {
#             "rich_text": _rich_text_list(text),
#             "icon": {"type": "emoji", "emoji": emoji},
#         },
#     }


# # ─────────────────────────────────────────────────────────────────────────────
# # Markdown table → Notion two-step table blocks
# # ─────────────────────────────────────────────────────────────────────────────

# def _parse_markdown_table(lines: list[str]) -> Optional[tuple[int, list[list[str]]]]:
#     """
#     Parse a markdown table block (already stripped of separator row).
#     Returns (column_count, [[cell, ...], ...]) or None if malformed.
#     """
#     rows: list[list[str]] = []
#     for line in lines:
#         line = line.strip()
#         if not line.startswith("|"):
#             break
#         # Remove leading/trailing pipes and split
#         cells = [c.strip() for c in line.strip("|").split("|")]
#         # Skip separator rows (---)
#         if all(re.match(r"^:?-+:?$", c) for c in cells if c):
#             continue
#         rows.append(cells)

#     if not rows:
#         return None

#     col_count = max(len(r) for r in rows)
#     # Pad short rows
#     padded = [r + [""] * (col_count - len(r)) for r in rows]
#     return col_count, padded


# def _table_shell_block(col_count: int, row_count: int, has_header: bool = True) -> dict:
#     """Create an empty Notion table shell (no rows — rows are appended separately)."""
#     return {
#         "object": "block",
#         "type": "table",
#         "table": {
#             "table_width": col_count,
#             "has_column_header": has_header,
#             "has_row_header": False,
#             "children": [],   # rows appended in Step 2
#         },
#     }


# def _table_row_block(cells: list[str]) -> dict:
#     return {
#         "object": "block",
#         "type": "table_row",
#         "table_row": {
#             "cells": [_rich_text_list(cell) for cell in cells],
#         },
#     }


# # ─────────────────────────────────────────────────────────────────────────────
# # Markdown → Notion blocks parser
# # ─────────────────────────────────────────────────────────────────────────────

# class _TablePending:
#     """Sentinel: a markdown table waiting for two-step Notion insertion."""
#     __slots__ = ("col_count", "rows")

#     def __init__(self, col_count: int, rows: list[list[str]]):
#         self.col_count = col_count
#         self.rows      = rows


# def _parse_content_to_blocks(content: str) -> list[Any]:
#     """
#     Convert full markdown document text to a list of Notion block dicts
#     (or _TablePending sentinels for tables).

#     Handles:
#       - # H1  ## H2  ### H3
#       - * / - / + bullets
#       - 1. numbered lists
#       - > blockquotes
#       - ``` fenced code blocks
#       - | markdown tables |
#       - --- horizontal rules
#       - Plain paragraphs (blank-line separated)
#     """
#     content = _preprocess_html_tables(content)
#     lines   = content.splitlines()
#     blocks: list[Any] = []

#     i = 0
#     in_code_block   = False
#     code_lines: list[str] = []
#     code_lang       = "plain text"

#     while i < len(lines):
#         line = lines[i]
#         stripped = line.strip()

#         # ── Fenced code block ─────────────────────────────────────────
#         if stripped.startswith("```"):
#             if not in_code_block:
#                 in_code_block = True
#                 lang_hint = stripped[3:].strip()
#                 code_lang = lang_hint if lang_hint else "plain text"
#                 code_lines = []
#             else:
#                 in_code_block = False
#                 code_text = "\n".join(code_lines)
#                 # Large code blocks: split into multiple code blocks
#                 for chunk_start in range(0, max(len(code_text), 1), MAX_TEXT_BLOCK):
#                     blocks.append(_code_block(code_text[chunk_start:chunk_start + MAX_TEXT_BLOCK], code_lang))
#                 code_lines = []
#             i += 1
#             continue

#         if in_code_block:
#             code_lines.append(line)
#             i += 1
#             continue

#         # ── Blank line ────────────────────────────────────────────────
#         if not stripped:
#             i += 1
#             continue

#         # ── Horizontal rule / divider ─────────────────────────────────
#         if re.match(r"^[-*_]{3,}$", stripped):
#             blocks.append(_divider_block())
#             i += 1
#             continue

#         # ── Heading ───────────────────────────────────────────────────
#         heading_match = re.match(r"^(#{1,3})\s+(.*)", stripped)
#         if heading_match:
#             level = len(heading_match.group(1))
#             text  = heading_match.group(2).strip()
#             blocks.append(_heading_block(level, text))
#             i += 1
#             continue

#         # ── Markdown table ────────────────────────────────────────────
#         if stripped.startswith("|") and "|" in stripped[1:]:
#             table_lines = []
#             while i < len(lines) and lines[i].strip().startswith("|"):
#                 table_lines.append(lines[i])
#                 i += 1
#             parsed = _parse_markdown_table(table_lines)
#             if parsed:
#                 col_count, rows = parsed
#                 blocks.append(_TablePending(col_count, rows))
#             else:
#                 # Fallback: render as code
#                 blocks.append(_code_block("\n".join(table_lines)))
#             continue

#         # ── Blockquote ────────────────────────────────────────────────
#         if stripped.startswith(">"):
#             text = re.sub(r"^>\s*", "", stripped)
#             # Collect multi-line quotes
#             quote_lines = [text]
#             i += 1
#             while i < len(lines) and lines[i].strip().startswith(">"):
#                 quote_lines.append(re.sub(r"^>\s*", "", lines[i].strip()))
#                 i += 1
#             blocks.append(_quote_block(" ".join(quote_lines)))
#             continue

#         # ── Bullet list ───────────────────────────────────────────────
#         bullet_match = re.match(r"^([*\-+])\s+(.*)", stripped)
#         if bullet_match:
#             text = bullet_match.group(2)
#             blocks.append(_bullet_block(text))
#             i += 1
#             continue

#         # ── Numbered list ─────────────────────────────────────────────
#         numbered_match = re.match(r"^\d+[.)]\s+(.*)", stripped)
#         if numbered_match:
#             text = numbered_match.group(1)
#             blocks.append(_numbered_block(text))
#             i += 1
#             continue

#         # ── Callout (custom DocForgeHub marker: "> 📌 text") ──────────
#         callout_match = re.match(r"^>\s*([\U0001F300-\U0001FAFF])\s+(.*)", stripped)
#         if callout_match:
#             emoji = callout_match.group(1)
#             text  = callout_match.group(2)
#             blocks.append(_callout_block(text, emoji))
#             i += 1
#             continue

#         # ── Paragraph (collect consecutive non-empty lines) ───────────
#         para_lines = []
#         while i < len(lines):
#             l = lines[i].strip()
#             if not l:
#                 break
#             if any([
#                 l.startswith("#"),
#                 l.startswith("|"),
#                 l.startswith(">"),
#                 re.match(r"^[*\-+]\s", l),
#                 re.match(r"^\d+[.)]\s", l),
#                 re.match(r"^[-*_]{3,}$", l),
#                 l.startswith("```"),
#             ]):
#                 break
#             para_lines.append(l)
#             i += 1

#         if para_lines:
#             text = " ".join(para_lines)
#             # Split very long paragraphs
#             for chunk_start in range(0, max(len(text), 1), MAX_TEXT_BLOCK):
#                 blocks.append(_paragraph_block(text[chunk_start:chunk_start + MAX_TEXT_BLOCK]))

#     return blocks


# # ─────────────────────────────────────────────────────────────────────────────
# # Two-step table appender
# # ─────────────────────────────────────────────────────────────────────────────

# def _append_table(notion: Client, page_id: str, pending: _TablePending) -> None:
#     """
#     Two-step Notion table creation:
#       1. Append empty table shell → capture block_id
#       2. Append table_row children to that block_id
#     """
#     shell = _table_shell_block(pending.col_count, len(pending.rows))
#     resp  = _call(
#         notion.blocks.children.append,
#         block_id=page_id,
#         children=[shell],
#     )
#     table_block_id = resp["results"][0]["id"]

#     # Append rows in batches of MAX_CHILDREN_BATCH
#     row_blocks = [_table_row_block(row) for row in pending.rows]
#     for batch_start in range(0, len(row_blocks), MAX_CHILDREN_BATCH):
#         batch = row_blocks[batch_start:batch_start + MAX_CHILDREN_BATCH]
#         _call(
#             notion.blocks.children.append,
#             block_id=table_block_id,
#             children=batch,
#         )


# # ─────────────────────────────────────────────────────────────────────────────
# # Batch block appender (handles tables inline + regular blocks)
# # ─────────────────────────────────────────────────────────────────────────────

# def _flush_regular_batch(notion: Client, page_id: str, batch: list[dict]) -> None:
#     if not batch:
#         return
#     for chunk_start in range(0, len(batch), MAX_CHILDREN_BATCH):
#         _call(
#             notion.blocks.children.append,
#             block_id=page_id,
#             children=batch[chunk_start:chunk_start + MAX_CHILDREN_BATCH],
#         )


# def _append_all_blocks(notion: Client, page_id: str, blocks: list[Any]) -> int:
#     """
#     Append all blocks (including _TablePending) to a Notion page.
#     Flushes regular blocks in SECTION_BLOCK_LIMIT batches, handles tables
#     via two-step API, and returns total sections (batches) written.
#     """
#     sections_written = 0
#     regular_batch: list[dict] = []

#     for block in blocks:
#         if isinstance(block, _TablePending):
#             # Flush pending regular blocks first
#             if regular_batch:
#                 _flush_regular_batch(notion, page_id, regular_batch)
#                 sections_written += math.ceil(len(regular_batch) / MAX_CHILDREN_BATCH)
#                 regular_batch = []
#             # Two-step table insert
#             _append_table(notion, page_id, block)
#             sections_written += 1
#         else:
#             regular_batch.append(block)
#             if len(regular_batch) >= SECTION_BLOCK_LIMIT:
#                 _flush_regular_batch(notion, page_id, regular_batch)
#                 sections_written += 1
#                 regular_batch = []

#     # Flush remainder
#     if regular_batch:
#         _flush_regular_batch(notion, page_id, regular_batch)
#         sections_written += math.ceil(len(regular_batch) / MAX_CHILDREN_BATCH)

#     return sections_written


# # ─────────────────────────────────────────────────────────────────────────────
# # Notion DB property helpers
# # ─────────────────────────────────────────────────────────────────────────────

# def _ensure_db_properties(notion: Client, database_id: str, required: dict[str, dict]) -> None:
#     """
#     Ensure the Notion database has all required properties.
#     Creates any missing ones. Silently skips 'title' (always exists).
#     """
#     try:
#         db       = _call(notion.databases.retrieve, database_id=database_id)
#         existing = {k.lower(): k for k in db.get("properties", {}).keys()}

#         updates: dict[str, dict] = {}
#         for prop_name, prop_schema in required.items():
#             if prop_name.lower() not in existing:
#                 updates[prop_name] = prop_schema
#                 logger.info("Creating missing DB property: '%s'", prop_name)

#         if updates:
#             _call(notion.databases.update, database_id=database_id, properties=updates)
#             logger.info("Added %d missing properties to Notion DB.", len(updates))

#     except Exception as exc:
#         # Non-fatal: log and continue. Publishing can still succeed.
#         logger.warning("Could not ensure DB properties: %s", exc)


# _REQUIRED_DB_PROPERTIES: dict[str, dict] = {
#     "Document Type": {"select": {}},
#     "Industry":      {"select": {}},
#     "Version":       {"rich_text": {}},
#     "Tags":          {"multi_select": {}},
#     "Created By":    {"rich_text": {}},
#     "Status":        {"select": {}},
#     "Source Template ID": {"rich_text": {}},
#     "Source Prompts":     {"rich_text": {}},
#     "Published At":  {"date": {}},
#     "Word Count":    {"number": {"format": "number"}},
# }


# def _build_page_properties(
#     title:              str,
#     doc_type:           Optional[str],
#     industry:           Optional[str],
#     version:            Optional[str],
#     tags:               Optional[list[str]],
#     created_by:         Optional[str],
#     status:             Optional[str],
#     source_template_id: Optional[str],
#     source_prompts:     Optional[str],
#     word_count:         int,
# ) -> dict:
#     """Build the Notion page properties dict for a new page."""
#     now_iso = datetime.now(timezone.utc).isoformat()

#     props: dict[str, Any] = {
#         "title": {
#             "title": [{"type": "text", "text": {"content": title[:255]}}]
#         },
#         "Published At": {"date": {"start": now_iso}},
#         "Word Count":   {"number": word_count},
#     }

#     if doc_type:
#         props["Document Type"] = {"select": {"name": doc_type[:100]}}
#     if industry:
#         props["Industry"]      = {"select": {"name": industry[:100]}}
#     if version:
#         props["Version"]       = {"rich_text": [_rich_text(version[:200])]}
#     if tags:
#         props["Tags"]          = {"multi_select": [{"name": t[:100]} for t in tags[:10]]}
#     if created_by:
#         props["Created By"]    = {"rich_text": [_rich_text(created_by[:200])]}
#     if status:
#         props["Status"]        = {"select": {"name": status[:100]}}
#     if source_template_id:
#         props["Source Template ID"] = {"rich_text": [_rich_text(source_template_id[:200])]}
#     if source_prompts:
#         # Notion rich-text max 2000 chars
#         props["Source Prompts"] = {"rich_text": [_rich_text(source_prompts[:2000])]}

#     return props


# # ─────────────────────────────────────────────────────────────────────────────
# # Public API
# # ─────────────────────────────────────────────────────────────────────────────

# def test_notion_connection(token: str, database_id: str) -> dict:
#     """
#     Verify Notion credentials and database access.
#     Returns {"success": True, "database_title": str} or {"success": False, "error": str}.
#     """
#     try:
#         notion = _get_client(token)
#         db     = _call(notion.databases.retrieve, database_id=database_id)

#         # Extract DB title
#         title_parts = db.get("title", [])
#         db_title    = "".join(p.get("plain_text", "") for p in title_parts) or "Untitled"

#         return {
#             "success":        True,
#             "database_id":    database_id,
#             "database_title": db_title,
#             "message":        f"Connected to Notion database: '{db_title}'",
#         }

#     except APIResponseError as exc:
#         msg = {
#             401: "Invalid Notion integration token. Check your secret_xxxx key.",
#             403: "Integration does not have access to this database. Share the database with your integration.",
#             404: "Database not found. Verify the database_id UUID.",
#         }.get(exc.status, f"Notion API error ({exc.status}): {exc.message}")
#         return {"success": False, "error": msg}

#     except Exception as exc:
#         return {"success": False, "error": f"Unexpected error: {exc}"}


# def publish_document_to_notion(
#     token:              str,
#     database_id:        str,
#     title:              str,
#     content:            str,
#     doc_type:           Optional[str] = None,
#     industry:           Optional[str] = None,
#     version:            Optional[str] = None,
#     tags:               Optional[list[str]] = None,
#     created_by:         Optional[str] = None,
#     status:             Optional[str] = None,
#     source_template_id: Optional[str] = None,
#     source_prompts:     Optional[str] = None,
#     skip_quality_gates: bool = False,
# ) -> dict:
#     """
#     Publish a full document to Notion as a flat, readable page.

#     Steps:
#       1. Quality gates (unless skip_quality_gates=True)
#       2. Ensure DB has all required properties (auto-create if missing)
#       3. Parse markdown content → Notion block list (including _TablePending)
#       4. Create Notion page with full metadata properties
#       5. Append all blocks in SECTION_BLOCK_LIMIT batches
#          - Regular blocks: batched append
#          - Tables: two-step API (shell → rows)

#     Returns:
#       {
#         "success": True,
#         "page_id": str,
#         "page_url": str,
#         "sections_written": int,
#         "total_blocks": int,
#         "word_count": int,
#       }
#     """
#     try:
#         notion = _get_client(token)

#         # ── 1. Quality Gates ───────────────────────────────────────────
#         if not skip_quality_gates:
#             try:
#                 run_quality_gates(content, doc_type=doc_type, title=title)
#             except QualityGateError as exc:
#                 return {"success": False, "error": f"Quality gate failed: {exc}"}

#         # ── 2. Ensure DB properties exist ─────────────────────────────
#         _ensure_db_properties(notion, database_id, _REQUIRED_DB_PROPERTIES)

#         # ── 3. Parse content → blocks ──────────────────────────────────
#         blocks     = _parse_content_to_blocks(content)
#         word_count = len(content.split())

#         logger.info(
#             "Parsed '%s' → %d blocks (%d words).",
#             title, len(blocks), word_count,
#         )

#         # ── 4. Create Notion page ──────────────────────────────────────
#         properties = _build_page_properties(
#             title              = title,
#             doc_type           = doc_type,
#             industry           = industry,
#             version            = version,
#             tags               = tags,
#             created_by         = created_by,
#             status             = status,
#             source_template_id = source_template_id,
#             source_prompts     = source_prompts,
#             word_count         = word_count,
#         )

#         page_resp = _call(
#             notion.pages.create,
#             parent     = {"database_id": database_id},
#             properties = properties,
#         )
#         page_id  = page_resp["id"]
#         page_url = page_resp.get("url", f"https://notion.so/{page_id.replace('-', '')}")

#         logger.info("Created Notion page: %s → %s", title, page_url)

#         # ── 5. Append all blocks ───────────────────────────────────────
#         sections_written = _append_all_blocks(notion, page_id, blocks)

#         logger.info(
#             "Published '%s' → %s | %d blocks | %d batches",
#             title, page_url, len(blocks), sections_written,
#         )

#         return {
#             "success":          True,
#             "page_id":          page_id,
#             "page_url":         page_url,
#             "sections_written": sections_written,
#             "total_blocks":     len(blocks),
#             "word_count":       word_count,
#         }

#     except APIResponseError as exc:
#         logger.error("Notion API error publishing '%s': %s", title, exc.message)
#         return {"success": False, "error": f"Notion API error ({exc.status}): {exc.message}"}

#     except Exception as exc:
#         logger.exception("Unexpected error publishing '%s'", title)
#         return {"success": False, "error": f"Unexpected error: {exc}"}


# def list_notion_pages(
#     token:       str,
#     database_id: str,
#     limit:       int = 20,
# ) -> dict:
#     """
#     List recently published pages from a Notion database.
#     Returns pages sorted by Published At descending.

#     Returns:
#       {
#         "success": True,
#         "pages": [
#           {
#             "page_id":    str,
#             "title":      str,
#             "doc_type":   str | None,
#             "industry":   str | None,
#             "status":     str | None,
#             "version":    str | None,
#             "tags":       list[str],
#             "created_by": str | None,
#             "word_count": int | None,
#             "page_url":   str,
#             "published_at": str | None,
#           },
#           ...
#         ],
#         "total": int,
#       }
#     """
#     try:
#         notion = _get_client(token)

#         response = _call(
#             notion.databases.query,
#             database_id  = database_id,
#             page_size    = min(limit, 100),
#             sorts        = [{"property": "Published At", "direction": "descending"}],
#         )

#         pages = []
#         for page in response.get("results", []):
#             props = page.get("properties", {})

#             def _get_title(p: dict) -> str:
#                 parts = p.get("title", {}).get("title", [])
#                 return "".join(x.get("plain_text", "") for x in parts)

#             def _get_select(p: dict, key: str) -> Optional[str]:
#                 s = p.get(key, {}).get("select")
#                 return s.get("name") if s else None

#             def _get_rich(p: dict, key: str) -> Optional[str]:
#                 parts = p.get(key, {}).get("rich_text", [])
#                 return "".join(x.get("plain_text", "") for x in parts) or None

#             def _get_multi(p: dict, key: str) -> list[str]:
#                 items = p.get(key, {}).get("multi_select", [])
#                 return [x.get("name", "") for x in items]

#             def _get_date(p: dict, key: str) -> Optional[str]:
#                 d = p.get(key, {}).get("date")
#                 return d.get("start") if d else None

#             def _get_number(p: dict, key: str) -> Optional[int]:
#                 return p.get(key, {}).get("number")

#             pages.append({
#                 "page_id":      page["id"],
#                 "title":        _get_title(props),
#                 "doc_type":     _get_select(props, "Document Type"),
#                 "industry":     _get_select(props, "Industry"),
#                 "status":       _get_select(props, "Status"),
#                 "version":      _get_rich(props, "Version"),
#                 "tags":         _get_multi(props, "Tags"),
#                 "created_by":   _get_rich(props, "Created By"),
#                 "word_count":   _get_number(props, "Word Count"),
#                 "page_url":     page.get("url", ""),
#                 "published_at": _get_date(props, "Published At"),
#             })

#         return {"success": True, "pages": pages, "total": len(pages)}

#     except APIResponseError as exc:
#         return {"success": False, "error": f"Notion API error ({exc.status}): {exc.message}"}

#     except Exception as exc:
#         logger.exception("Unexpected error listing pages")
#         return {"success": False, "error": f"Unexpected error: {exc}"}


# def update_page_status(
#     token:   str,
#     page_id: str,
#     status:  str,
# ) -> dict:
#     """
#     Update the Status property of an existing Notion page.
#     Useful for marking documents as Reviewed, Archived, etc.
#     """
#     try:
#         notion = _get_client(token)
#         _call(
#             notion.pages.update,
#             page_id    = page_id,
#             properties = {"Status": {"select": {"name": status[:100]}}},
#         )
#         return {"success": True, "page_id": page_id, "status": status}

#     except APIResponseError as exc:
#         return {"success": False, "error": f"Notion API error ({exc.status}): {exc.message}"}

#     except Exception as exc:
#         return {"success": False, "error": f"Unexpected error: {exc}"}
    
#------------------------------------------------------------

# """
# Notion Integration Service
# ──────────────────────────
# Features:
#   - Publishes FULL documents — every section, every table, every paragraph
#   - Flat readable pages: headings + content directly on page, no toggles
#   - Full markdown TABLE support via Notion's two-step API:
#       Step 1: append empty table shell → get block_id
#       Step 2: append table_row children to that block_id
#   - HTML table fallback: converts <table> HTML to markdown before parsing
#   - Rate-limit aware with exponential backoff
#   - Smart block parser: h1/h2/h3, bullets, numbered, quotes, dividers, tables, paragraphs
#   - Full metadata: type, industry, version, tags, created_by, status, source
# """

# import re
# import time
# import logging
# from typing import Optional, Callable
# from notion_client import Client
# from notion_client.errors import APIResponseError

# logger = logging.getLogger(__name__)

# # ─────────────────────────────────────────────
# # Constants
# # ─────────────────────────────────────────────

# MAX_BLOCK_CHARS     = 2000
# MAX_CHILDREN_BATCH  = 100
# SECTION_BLOCK_LIMIT = 80
# RATE_LIMIT_RETRIES  = 5
# RATE_LIMIT_BACKOFF  = 2.0


# # ─────────────────────────────────────────────
# # Client + Rate-limit wrapper
# # ─────────────────────────────────────────────

# def _get_client(token: str) -> Client:
#     return Client(auth=token)


# def _call(fn, *args, **kwargs):
#     """Retry on 429 with exponential backoff."""
#     delay = RATE_LIMIT_BACKOFF
#     for attempt in range(RATE_LIMIT_RETRIES + 1):
#         try:
#             return fn(*args, **kwargs)
#         except APIResponseError as e:
#             if e.status == 429 and attempt < RATE_LIMIT_RETRIES:
#                 logger.warning(f"Rate limited. Waiting {delay:.1f}s (attempt {attempt+1})...")
#                 time.sleep(delay)
#                 delay *= 2
#             else:
#                 raise


# # ─────────────────────────────────────────────
# # 1. Test Connection
# # ─────────────────────────────────────────────

# def test_notion_connection(token: str, database_id: str) -> dict:
#     try:
#         notion    = _get_client(token)
#         db        = _call(notion.databases.retrieve, database_id=database_id)
#         title_arr = db.get("title", [])
#         db_name   = title_arr[0]["plain_text"] if title_arr else "Untitled"
#         return {
#             "success":       True,
#             "database_name": db_name,
#             "properties":    list(db.get("properties", {}).keys()),
#         }
#     except APIResponseError as e:
#         return {"success": False, "error": _map_error(e)}
#     except Exception as e:
#         return {"success": False, "error": str(e)}


# # ─────────────────────────────────────────────
# # 2. Publish Document
# # ─────────────────────────────────────────────

# def publish_document_to_notion(
#     token:              str,
#     database_id:        str,
#     title:              str,
#     content:            str,
#     doc_type:           Optional[str]       = None,
#     industry:           Optional[str]       = None,
#     version:            Optional[str]       = None,
#     tags:               Optional[list[str]] = None,
#     created_by:         Optional[str]       = None,
#     status:             Optional[str]       = None,
#     source_template_id: Optional[str]       = None,
#     source_prompts:     Optional[str]       = None,
#     extra_properties:   Optional[dict]      = None,
#     on_progress:        Optional[Callable]  = None,
# ) -> dict:
#     """
#     Publish a full document to Notion as a flat readable page.

#     Content is normalized before parsing — HTML tables, escaped markdown,
#     and other LLM output quirks are cleaned up so nothing is lost.

#     Every section is appended as: ## Heading → content blocks → divider.
#     Tables are handled via Notion's two-step API (shell + rows).
#     """
#     try:
#         notion = _get_client(token)

#         # ── Normalize content ─────────────────────────────────────────
#         content = _normalize_content(content)

#         # ── DB schema ─────────────────────────────────────────────────
#         db         = _call(notion.databases.retrieve, database_id=database_id)
#         db_props   = db.get("properties", {})
#         title_prop = _find_title_property(db)

#         # ── Properties ────────────────────────────────────────────────
#         properties: dict = {
#             title_prop: {"title": [{"text": {"content": title[:2000]}}]}
#         }

#         def _sel(col, val):
#             if val and col in db_props:
#                 properties[col] = {"select": {"name": str(val)[:100]}}

#         def _txt(col, val):
#             if val and col in db_props:
#                 properties[col] = {"rich_text": [{"text": {"content": str(val)[:2000]}}]}

#         def _multi(col, vals):
#             if vals and col in db_props:
#                 properties[col] = {"multi_select": [{"name": t[:100]} for t in vals]}

#         _sel("Status",   status)
#         _sel("Type",     doc_type)
#         _sel("Industry", industry)
#         _sel("Version",  version)
#         _multi("Tags", tags)
#         _txt("Created By",         created_by)
#         _txt("Source Template ID", source_template_id)

#         if extra_properties:
#             properties.update(extra_properties)

#         # ── Split into sections ───────────────────────────────────────
#         sections = _split_into_sections(content)
#         total    = len(sections)
#         logger.info(f"Document split into {total} sections for '{title}'")

#         # ── Create page with TOC only ─────────────────────────────────
#         initial_children: list[dict] = []

#         if source_prompts or source_template_id:
#             info_lines = []
#             if source_template_id:
#                 info_lines.append(f"Template ID: {source_template_id}")
#             if source_prompts:
#                 info_lines.append(f"Prompts: {source_prompts[:400]}")
#             initial_children.append(_callout_block("📎 Source Info", "\n".join(info_lines)))

#         initial_children.append(_callout_block(
#             "📄 Table of Contents",
#             "\n".join(f"  {i+1}. {s['label']}" for i, s in enumerate(sections)),
#         ))

#         response = _call(
#             notion.pages.create,
#             parent={"database_id": database_id},
#             properties=properties,
#             children=initial_children,
#         )
#         page_id  = response["id"]
#         page_url = response.get("url", "")
#         logger.info(f"Page created: {page_id} — appending {total} sections")

#         # ── Append all sections ───────────────────────────────────────
#         for i, section in enumerate(sections, start=1):
#             flat_blocks = (
#                 [_heading_block(section["label"], 2)]
#                 + section["blocks"]
#                 + [{"object": "block", "type": "divider", "divider": {}}]
#             )
#             _append_blocks_smart(notion, page_id, flat_blocks)

#             logger.info(f"  ✓ Section {i}/{total}: '{section['label']}'")
#             if on_progress:
#                 on_progress(i, total, section["label"])
#             if i < total:
#                 time.sleep(0.35)

#         logger.info(f"Publish complete: {total} sections → {page_url}")
#         return {
#             "success":          True,
#             "page_id":          page_id,
#             "page_url":         page_url,
#             "sections_written": total,
#         }

#     except APIResponseError as e:
#         msg = _map_error(e)
#         logger.error(f"Notion API error: {msg}")
#         return {"success": False, "error": msg}
#     except Exception as e:
#         logger.exception("Unexpected error during Notion publish")
#         return {"success": False, "error": str(e)}


# # ─────────────────────────────────────────────
# # 3. List Pages
# # ─────────────────────────────────────────────

# def list_notion_pages(token: str, database_id: str, limit: int = 20) -> dict:
#     try:
#         notion   = _get_client(token)
#         response = _call(
#             notion.databases.query,
#             database_id=database_id,
#             page_size=limit,
#             sorts=[{"timestamp": "created_time", "direction": "descending"}],
#         )
#         pages = [
#             {
#                 "id":         p["id"],
#                 "title":      _extract_title(p),
#                 "url":        p.get("url", ""),
#                 "created_at": p.get("created_time", ""),
#             }
#             for p in response.get("results", [])
#         ]
#         return {"success": True, "pages": pages}
#     except APIResponseError as e:
#         return {"success": False, "error": _map_error(e)}
#     except Exception as e:
#         return {"success": False, "error": str(e)}


# # ─────────────────────────────────────────────
# # Content Normalizer
# # Cleans LLM output before parsing so nothing is lost.
# # Handles: HTML tables, escaped chars, smart quotes, etc.
# # ─────────────────────────────────────────────

# def _normalize_content(text: str) -> str:
#     """
#     Normalize raw LLM / template content into clean markdown.

#     1. Convert HTML <table> blocks to markdown pipe tables
#     2. Convert HTML <br> to newlines
#     3. Strip remaining HTML tags
#     4. Fix escaped markdown sequences
#     5. Normalize smart quotes and dashes
#     """
#     if not text:
#         return text

#     # ── 1. Convert HTML tables → markdown ────────────────────────────
#     text = _html_tables_to_markdown(text)

#     # ── 2. HTML line breaks → newlines ───────────────────────────────
#     text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

#     # ── 3. Strip remaining HTML tags ─────────────────────────────────
#     text = re.sub(r"<[^>]+>", "", text)

#     # ── 4. Decode HTML entities ───────────────────────────────────────
#     text = text.replace("&amp;",  "&")
#     text = text.replace("&lt;",   "<")
#     text = text.replace("&gt;",   ">")
#     text = text.replace("&nbsp;", " ")
#     text = text.replace("&#39;",  "'")
#     text = text.replace("&quot;", '"')

#     # ── 5. Normalize smart quotes / dashes ────────────────────────────
#     text = text.replace("\u2018", "'").replace("\u2019", "'")
#     text = text.replace("\u201c", '"').replace("\u201d", '"')
#     text = text.replace("\u2013", "-").replace("\u2014", "--")

#     # ── 6. Remove excessive blank lines (max 2 consecutive) ──────────
#     text = re.sub(r"\n{3,}", "\n\n", text)

#     return text.strip()


# def _html_tables_to_markdown(text: str) -> str:
#     """Convert all HTML <table>...</table> blocks to markdown pipe tables."""

#     def convert_table(match):
#         html = match.group(0)
#         rows = []

#         # Extract all rows
#         for row_match in re.finditer(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE):
#             row_html = row_match.group(1)
#             cells = []
#             # Match both <th> and <td>
#             for cell_match in re.finditer(r"<t[hd][^>]*>(.*?)</t[hd]>", row_html, re.DOTALL | re.IGNORECASE):
#                 cell_text = re.sub(r"<[^>]+>", "", cell_match.group(1))  # strip inner tags
#                 cell_text = cell_text.replace("\n", " ").strip()
#                 cells.append(cell_text)
#             if cells:
#                 rows.append(cells)

#         if not rows:
#             return ""

#         col_count = max(len(r) for r in rows)
#         padded    = [r + [""] * (col_count - len(r)) for r in rows]

#         md_lines = []
#         md_lines.append("| " + " | ".join(padded[0]) + " |")
#         md_lines.append("| " + " | ".join(["---"] * col_count) + " |")
#         for row in padded[1:]:
#             md_lines.append("| " + " | ".join(row) + " |")

#         return "\n".join(md_lines) + "\n"

#     return re.sub(r"<table[^>]*>.*?</table>", convert_table, text, flags=re.DOTALL | re.IGNORECASE)


# # ─────────────────────────────────────────────
# # Smart Block Appender
# #
# # Notion table API requires TWO separate calls:
# #   Call 1 → append empty table shell → returns table block_id
# #   Call 2 → append table_row blocks to that table block_id
# #
# # All non-table blocks are batched (up to MAX_CHILDREN_BATCH per call).
# # ─────────────────────────────────────────────

# def _append_blocks_smart(notion: Client, page_id: str, blocks: list[dict]):
#     batch: list[dict] = []

#     def flush_batch():
#         if not batch:
#             return
#         _call(notion.blocks.children.append, block_id=page_id, children=list(batch))
#         batch.clear()

#     for block in blocks:
#         if block.get("type") == "table":
#             flush_batch()  # send pending normal blocks first

#             rows       = block.pop("_rows")
#             col_count  = block["table"]["table_width"]
#             has_header = block["table"]["has_column_header"]

#             # Step 1: Create empty table shell
#             table_shell = {
#                 "object": "block",
#                 "type":   "table",
#                 "table": {
#                     "table_width":       col_count,
#                     "has_column_header": has_header,
#                     "has_row_header":    False,
#                 },
#             }
#             resp           = _call(notion.blocks.children.append, block_id=page_id, children=[table_shell])
#             table_block_id = resp["results"][0]["id"]
#             logger.info(f"    Table shell created ({col_count} cols, {len(rows)} rows): {table_block_id}")

#             # Step 2: Append rows to the table block
#             for batch_start in range(0, len(rows), MAX_CHILDREN_BATCH):
#                 _call(
#                     notion.blocks.children.append,
#                     block_id=table_block_id,
#                     children=rows[batch_start : batch_start + MAX_CHILDREN_BATCH],
#                 )
#             time.sleep(0.2)

#         else:
#             batch.append(block)
#             if len(batch) >= MAX_CHILDREN_BATCH:
#                 flush_batch()

#     flush_batch()


# # ─────────────────────────────────────────────
# # Section Splitter
# # ─────────────────────────────────────────────

# def _split_into_sections(text: str) -> list[dict]:
#     if not text.strip():
#         return [{"label": "Content", "blocks": [_paragraph_block("(empty document)")]}]

#     lines         = text.splitlines()
#     chunks        = []
#     current_label = "Introduction"
#     current_lines: list[str] = []

#     for line in lines:
#         h1 = re.match(r"^#\s+(.*)",  line.strip())
#         h2 = re.match(r"^##\s+(.*)", line.strip())
#         heading = h1 or h2
#         if heading:
#             if current_lines:
#                 chunks.append({"label": current_label, "lines": list(current_lines)})
#             current_label = heading.group(1).strip()[:80]
#             current_lines = []
#         else:
#             current_lines.append(line)

#     if current_lines or not chunks:
#         chunks.append({"label": current_label, "lines": current_lines})

#     sections = []
#     for chunk in chunks:
#         raw    = "\n".join(chunk["lines"])
#         blocks = _content_to_blocks(raw)
#         if not blocks:
#             continue
#         if len(blocks) <= SECTION_BLOCK_LIMIT:
#             sections.append({"label": chunk["label"], "blocks": blocks})
#         else:
#             for part_num, i in enumerate(range(0, len(blocks), SECTION_BLOCK_LIMIT), start=1):
#                 sections.append({
#                     "label":  f"{chunk['label']} (Part {part_num})",
#                     "blocks": blocks[i : i + SECTION_BLOCK_LIMIT],
#                 })

#     return sections or [{"label": "Content", "blocks": _content_to_blocks(text)}]


# # ─────────────────────────────────────────────
# # Content → Notion Blocks
# # ─────────────────────────────────────────────

# def _content_to_blocks(text: str) -> list[dict]:
#     """
#     Parse clean markdown text into Notion block objects.

#     Supported:
#       # h1   ## h2   ### h3
#       - / * / • bullets
#       1. / 1) numbered lists
#       > blockquotes
#       --- dividers
#       | markdown tables |
#       plain paragraphs
#     """
#     if not text.strip():
#         return []

#     all_blocks: list[dict] = []
#     para_buf:   list[str]  = []
#     table_buf:  list[str]  = []
#     in_table = False

#     def flush_para():
#         joined = " ".join(para_buf).strip()
#         para_buf.clear()
#         if not joined:
#             return
#         for chunk in _chunks(joined):
#             all_blocks.append(_paragraph_block(chunk))

#     def flush_table():
#         if not table_buf:
#             return
#         tbl = _build_table_block(list(table_buf))
#         if tbl:
#             all_blocks.append(tbl)
#         table_buf.clear()

#     for line in text.splitlines():
#         s = line.strip()

#         # ── Table detection ──────────────────────────────────────────
#         if s.startswith("|") and "|" in s[1:]:
#             if not in_table:
#                 flush_para()
#                 in_table = True
#             table_buf.append(s)
#             continue
#         else:
#             if in_table:
#                 flush_table()
#                 in_table = False

#         if not s:
#             flush_para()
#             continue

#         # Headings
#         h3 = re.match(r"^###\s+(.*)", s)
#         h2 = re.match(r"^##\s+(.*)",  s)
#         h1 = re.match(r"^#\s+(.*)",   s)
#         if h3: flush_para(); all_blocks.append(_heading_block(h3.group(1), 3)); continue
#         if h2: flush_para(); all_blocks.append(_heading_block(h2.group(1), 2)); continue
#         if h1: flush_para(); all_blocks.append(_heading_block(h1.group(1), 1)); continue

#         # Bullet list
#         bullet = re.match(r"^[-*•]\s+(.*)", s)
#         if bullet:
#             flush_para()
#             for c in _chunks(bullet.group(1)):
#                 all_blocks.append(_bullet_block(c))
#             continue

#         # Numbered list
#         numbered = re.match(r"^\d+[.)]\s+(.*)", s)
#         if numbered:
#             flush_para()
#             for c in _chunks(numbered.group(1)):
#                 all_blocks.append(_numbered_block(c))
#             continue

#         # Blockquote
#         quote = re.match(r"^>\s+(.*)", s)
#         if quote:
#             flush_para()
#             all_blocks.append(_quote_block(quote.group(1)[:2000]))
#             continue

#         # Divider
#         if re.match(r"^[-_*]{3,}$", s):
#             flush_para()
#             all_blocks.append({"object": "block", "type": "divider", "divider": {}})
#             continue

#         para_buf.append(s)

#     # Flush remaining buffers
#     if in_table:
#         flush_table()
#     flush_para()

#     return all_blocks


# def _build_table_block(table_lines: list[str]) -> Optional[dict]:
#     """
#     Build a table block from markdown table lines.

#     Rows are stored under internal key "_rows" — NOT sent to Notion directly.
#     _append_blocks_smart reads "_rows" and uses the two-step table API.
#     """
#     rows = []
#     for line in table_lines:
#         s = line.strip()
#         # Skip separator lines: |---|---|
#         if re.match(r"^\|[\s\-:|]+\|$", s):
#             continue
#         cells = [c.strip() for c in s.strip("|").split("|")]
#         if any(c for c in cells):
#             rows.append(cells)

#     if not rows:
#         return None

#     col_count = max(len(r) for r in rows)
#     padded    = [r + [""] * (col_count - len(r)) for r in rows]

#     notion_rows = []
#     for row in padded:
#         cells = []
#         for cell in row:
#             cells.append([{"type": "text", "text": {"content": cell[:2000]}}])
#         notion_rows.append({
#             "object":    "block",
#             "type":      "table_row",
#             "table_row": {"cells": cells},
#         })

#     return {
#         "object": "block",
#         "type":   "table",
#         "_rows":  notion_rows,      # ← internal staging key
#         "table": {
#             "table_width":       col_count,
#             "has_column_header": True,
#             "has_row_header":    False,
#         },
#     }


# # ─────────────────────────────────────────────
# # Block Constructors
# # ─────────────────────────────────────────────

# def _chunks(text: str) -> list[str]:
#     return [text[i:i + MAX_BLOCK_CHARS] for i in range(0, max(len(text), 1), MAX_BLOCK_CHARS)]

# def _rt(content: str) -> list[dict]:
#     return [{"type": "text", "text": {"content": content}}]

# def _paragraph_block(content: str) -> dict:
#     return {"object": "block", "type": "paragraph",
#             "paragraph": {"rich_text": _rt(content)}}

# def _heading_block(content: str, level: int) -> dict:
#     t = f"heading_{level}"
#     return {"object": "block", "type": t, t: {"rich_text": _rt(content[:2000])}}

# def _bullet_block(content: str) -> dict:
#     return {"object": "block", "type": "bulleted_list_item",
#             "bulleted_list_item": {"rich_text": _rt(content)}}

# def _numbered_block(content: str) -> dict:
#     return {"object": "block", "type": "numbered_list_item",
#             "numbered_list_item": {"rich_text": _rt(content)}}

# def _quote_block(content: str) -> dict:
#     return {"object": "block", "type": "quote",
#             "quote": {"rich_text": _rt(content)}}

# def _callout_block(title: str, body: str) -> dict:
#     return {
#         "object": "block", "type": "callout",
#         "callout": {
#             "rich_text": _rt(f"{title}\n{body}"[:2000]),
#             "icon":      {"type": "emoji", "emoji": "📎"},
#             "color":     "gray_background",
#         },
#     }


# # ─────────────────────────────────────────────
# # Helpers
# # ─────────────────────────────────────────────

# def _find_title_property(db: dict) -> str:
#     for name, prop in db.get("properties", {}).items():
#         if prop.get("type") == "title":
#             return name
#     return "Name"

# def _extract_title(page: dict) -> str:
#     for prop in page.get("properties", {}).values():
#         if prop.get("type") == "title":
#             arr = prop.get("title", [])
#             if arr:
#                 return arr[0].get("plain_text", "Untitled")
#     return "Untitled"

# def _map_error(e: APIResponseError) -> str:
#     return {
#         "unauthorized":        "Invalid integration token.",
#         "object_not_found":    "Database not found — share it with your integration.",
#         "restricted_resource": "Integration has no access to this database.",
#         "validation_error":    f"Notion validation error: {e.message}",
#         "rate_limited":        "Rate limited — please retry in a moment.",
#     }.get(e.code, f"Notion API error ({e.code}): {e.message}")
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