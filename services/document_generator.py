import os
import re
from dotenv import load_dotenv
from utils.logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)

# ============================================================
# DEPARTMENT CONTEXT
# ============================================================
DEPT_CONTEXT = {
    "HR & People Operations": {
        "focus": "people management, talent acquisition, employee lifecycle, culture, and HR compliance",
        "tone_note": "empathetic, people-first, clear and inclusive language",
        "compliance_note": "employment law, GDPR, equal opportunity regulations",
        "tools": "BambooHR, Slack, Google Workspace, JIRA",
    },
    "Legal & Compliance": {
        "focus": "legal risk management, regulatory compliance, contracts, and corporate governance",
        "tone_note": "precise, formal, unambiguous legal language",
        "compliance_note": "GDPR, SOC2, ISO27001, local employment law",
        "tools": "DocuSign, Confluence",
    },
    "Sales & Customer Facing": {
        "focus": "revenue generation, customer relationships, deal management",
        "tone_note": "confident, persuasive, customer-centric language",
        "compliance_note": "GDPR, fair trade practices",
        "tools": "Salesforce, HubSpot, Zendesk",
    },
    "Engineering & Operations": {
        "focus": "software development lifecycle, system reliability, DevOps",
        "tone_note": "technical, precise, structured with clear steps",
        "compliance_note": "SOC2, ISO27001, change management",
        "tools": "JIRA, GitHub, Kubernetes, Datadog",
    },
    # Add other departments only when needed (kept minimal for cleanliness)
    "_default": {
        "focus": "professional operations",
        "tone_note": "professional and clear",
        "compliance_note": "standard industry compliance",
        "tools": "Standard tools",
    }
}

# ============================================================
# DOCUMENT LENGTH MAP (Shortened - kept essential ones)
# ============================================================
DOCUMENT_LENGTH_MAP = {
    "Offer Letter":                      {"min_pages": 1,  "max_pages": 1,  "target_words": 200},
    "Employment Contract":               {"min_pages": 4,  "max_pages": 8,  "target_words": 4000},
    "Employee Handbook":                 {"min_pages": 35, "max_pages": 40, "target_words": 13000},
    "NDA":                               {"min_pages": 3,  "max_pages": 6,  "target_words": 2000},
    "Privacy Policy":                    {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
    "Sales Proposal Template":           {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
    "Software Requirements Specification (SRS)": {"min_pages": 10, "max_pages": 20, "target_words": 6000},
    "_default":                          {"min_pages": 4,  "max_pages": 8,  "target_words": 3000},
}

ONE_PAGE_DOCS = {"Offer Letter", "Press Release Template"}


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def clean_generated_content(content: str) -> str:
    """Clean unwanted HTML tags and excessive newlines."""
    content = re.sub(r'</?(?:div|span|p|br)[^>]*>', '', content)
    content = re.sub(r'\n{4,}', '\n\n\n', content)
    return content.strip()


def get_department_context(department: str):
    """Return department context or default."""
    return DEPT_CONTEXT.get(department, DEPT_CONTEXT["_default"])


def get_document_specs(document_type: str, doc_specs=None):
    """Merge default specs with custom specs."""
    length_map = DOCUMENT_LENGTH_MAP.get(document_type, DOCUMENT_LENGTH_MAP["_default"])
    if doc_specs:
        return {**length_map, **{k: v for k, v in doc_specs.items() if v is not None}}
    return length_map


# ============================================================
# PROMPT BUILDER (Clean & Modular)
# ============================================================
def build_prompt(
    industry: str,
    department: str,
    document_type: str,
    question_answers: dict,
    sections: list = None,
    doc_specs: dict = None,
    is_regeneration: bool = False,
    original_content: str = "",
):
    dept = get_department_context(department)
    specs = get_document_specs(document_type, doc_specs)

    # Extract common fields
    company_name = question_answers.get("company_name", "the company")
    company_size = question_answers.get("company_size", "51-200")
    primary_product = question_answers.get("primary_product", "SaaS platform")
    target_market = question_answers.get("target_market", "B2B")

    tools = question_answers.get("tools_used", dept.get("tools", ""))
    tools_str = ", ".join(tools) if isinstance(tools, list) else str(tools)

    compliance = question_answers.get("compliance_requirements") or dept["compliance_note"]
    compliance_str = ", ".join(compliance) if isinstance(compliance, list) else str(compliance)

    # Extra user answers
    skip_keys = {"company_name", "company_size", "primary_product", "target_market",
                 "tools_used", "compliance_requirements", "specific_focus",
                 "additional_context", "document_title", "author_name", "approved_by"}

    extra_answers = "\n".join(
        f"  - {k.replace('_', ' ').title()}: {', '.join(v) if isinstance(v, list) else v}"
        for k, v in question_answers.items()
        if k not in skip_keys and v and str(v) not in ("(select)", "", "None")
    )

    focus_block = ""
    if question_answers.get("specific_focus"):
        focus_block += f"\nSPECIFIC FOCUS: {question_answers['specific_focus']}"
    if question_answers.get("additional_context") or question_answers.get("additional_ctx"):
        focus_block += f"\nADDITIONAL CONTEXT: {question_answers.get('additional_context') or question_answers.get('additional_ctx')}"
    if extra_answers:
        focus_block += f"\nUSER DETAILS:\n{extra_answers}"

    # 1-Page Documents
    if document_type in ONE_PAGE_DOCS or (specs["min_pages"] == 1 and specs["max_pages"] == 1):
        return f"""Write a professional {document_type} for {company_name}.

STRICT RULE: Write EXACTLY 150-200 words. Plain text letter ONLY.
NO markdown, NO headers, NO bullets, NO tables.
STRUCTURE: Date → Greeting → 2-3 paragraphs → Closing → Signature.

DETAILS:
- Company: {company_name}
- Recipient: {question_answers.get('candidate_name') or question_answers.get('recipient_name', '[Name]')}
- Role: {question_answers.get('job_title') or question_answers.get('position', '[Job Title]')}
- Compensation: {question_answers.get('salary') or question_answers.get('compensation', '[Salary]')}
- Start Date: {question_answers.get('start_date') or question_answers.get('joining_date', '[Date]')}

{focus_block}

Write the {document_type} now (150-200 words only):"""

    # Regeneration Mode
    if is_regeneration and original_content:
        return f"""Enhance this {document_type} for {company_name}.
Improve quality, clarity, and compliance ({compliance_str}).
Target: {specs['target_words']:,} words.

ORIGINAL:
{original_content[:2500]}

Write the enhanced full version now:"""

    # Standard Multi-page Document
    sections_block = "REQUIRED SECTIONS:\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(sections)) if sections else ""

    return f"""You are a senior enterprise documentation specialist.
Write a COMPLETE {document_type} for {company_name}.

COMPANY INFO:
- Name: {company_name} ({company_size} employees)
- Industry: {industry} | Product: {primary_product} | Market: {target_market}
- Department: {department} — {dept['focus']}
- Tools: {tools_str}
- Compliance: {compliance_str}

DOCUMENT:
- Title: {question_answers.get('document_title', document_type)}
- Version: {question_answers.get('document_version', '1.0')}
- Author: {question_answers.get('author_name', department + ' Team')}
- Approver: {question_answers.get('approved_by', 'Management')}

{sections_block}
{focus_block}

RULES:
1. Use "{company_name}" — never "the company"
2. No placeholders like [Insert], TBD
3. Tone: {dept['tone_note']}
4. Format: ## Section, ### Subsection, **bold**, tables where useful
5. Each section minimum 250 words with real details
6. End with Version History table

Write the FULL {document_type.upper()} now:"""


# ============================================================
# MAIN GENERATION FUNCTION (Single Clean Function)
# ============================================================
def generate_document(
    industry: str,
    department: str,
    document_type: str,
    question_answers: dict,
    is_regeneration: bool = False,
    original_content: str = "",
):
    """Main function to generate professional documents using Azure OpenAI."""
    logger.info(f"Generating: {document_type} | {department} | {question_answers.get('company_name', 'N/A')}")

    sections = []
    doc_specs = {}

    # Try to load template & questionnaire (optional - graceful fallback)
    try:
        from services.template_repository import get_template_by_type
        from services.questionnaire_repository import get_questionnaire_by_type

        template = get_template_by_type(document_type, department)
        if template:
            sections = template.get("structure", {}).get("sections", [])

        questionnaire = get_questionnaire_by_type(department, document_type)
        if questionnaire:
            for q in questionnaire.get("questions", []):
                if q.get("id") == "_document_specs":
                    doc_specs = q.get("document_specs", {})
                    break
    except Exception as e:
        logger.warning(f"Template/Questionnaire load failed: {e}")

    specs = get_document_specs(document_type, doc_specs)
    target_words = specs["target_words"]
    is_one_page = document_type in ONE_PAGE_DOCS or (specs["min_pages"] == 1 and specs["max_pages"] == 1)

    # Build prompt
    prompt = build_prompt(
        industry, department, document_type, question_answers,
        sections, specs, is_regeneration, original_content
    )

    # Azure OpenAI Configuration
    endpoint = os.getenv("AZURE_LLM_ENDPOINT", "").rstrip("/")
    api_key = os.getenv("AZURE_OPENAI_LLM_KEY") or os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    api_version = os.getenv("AZURE_LLM_API_VERSION", "2025-01-01-preview")
    deployment = os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI") or os.getenv("AZURE_OPENAI_DEPLOYMENT") or "gpt-4.1-mini"

    if not endpoint or not api_key:
        raise ValueError("Missing Azure OpenAI credentials in .env file")

    # Token & Temperature settings
    est_tokens = int(target_words * 1.35)
    if is_one_page:
        max_tokens, temperature = 300, 0.1
    elif specs["max_pages"] <= 5:
        max_tokens, temperature = min(est_tokens + 1000, 6000), 0.4
    else:
        max_tokens, temperature = min(est_tokens + 4000, 14000), 0.5

    if is_regeneration:
        max_tokens = min(max_tokens + 2000, 16000)
        temperature = max(temperature - 0.1, 0.1)

    logger.info(f"Calling Azure OpenAI | max_tokens={max_tokens} | temp={temperature}")

    try:
        from openai import AzureOpenAI
        import httpx

        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
            http_client=httpx.Client(),
        )

        system_msg = (
            "You are a professional business writer. Write EXACTLY 150-200 words in plain text only."
            if is_one_page else
            "You are a senior enterprise documentation specialist. Write COMPLETE, detailed, professional documents. "
            "Every section must be substantial (min 250 words). Never stop early."
        )

        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "system", "content": system_msg},
                      {"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = clean_generated_content(response.choices[0].message.content)

        # Continuation logic for long documents
        if (response.choices[0].finish_reason == "length" and
                not is_one_page and
                len(content.split()) < target_words * 0.7):

            logger.info("Generating continuation part...")
            cont_response = client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": f"Continue from where you stopped. Complete all remaining sections. Target: {target_words} words. Start immediately:"}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content += "\n\n" + clean_generated_content(cont_response.choices[0].message.content)

        return content

    except ImportError:
        raise ImportError("Please install: pip install openai httpx")
    except Exception as e:
        logger.error(f"Document generation failed: {e}", exc_info=True)
        raise RuntimeError(f"Azure OpenAI error: {e}") from e
# """
# Document Generator — Smart Dynamic Prompt System v2
# Uses Azure OpenAI SDK directly.

# ARCHITECTURE:
# - DOCUMENT_LENGTH_MAP: page/word specs per document type
# - Smart prompt builder — AI generates content intelligently
# - 1-page documents handled separately (Offer Letter etc.)
# - Continuation support for incomplete documents
# """

# import os
# from dotenv import load_dotenv
# from utils.logger import setup_logger

# load_dotenv()
# logger = setup_logger(__name__)


# # ============================================================
# # DEPARTMENT CONTEXT
# # ============================================================
# DEPT_CONTEXT = {
#     "HR & People Operations": {
#         "focus": "people management, talent acquisition, employee lifecycle, culture, and HR compliance",
#         "tone_note": "empathetic, people-first, clear and inclusive language",
#         "compliance_note": "employment law, GDPR for employee data, equal opportunity regulations",
#         "tools": "BambooHR, Slack, Google Workspace, JIRA, Confluence",
#     },
#     "Legal & Compliance": {
#         "focus": "legal risk management, regulatory compliance, contracts, and corporate governance",
#         "tone_note": "precise, formal, unambiguous legal language",
#         "compliance_note": "GDPR, SOC2, ISO27001, local employment law, CCPA, anti-bribery laws",
#         "tools": "DocuSign, Confluence, Legal tracking tools",
#     },
#     "Sales & Customer Facing": {
#         "focus": "revenue generation, customer relationships, deal management, and customer retention",
#         "tone_note": "confident, persuasive, customer-centric language",
#         "compliance_note": "GDPR for customer data, fair trade practices, CRM data privacy",
#         "tools": "Salesforce, HubSpot, Zendesk, Slack",
#     },
#     "Engineering & Operations": {
#         "focus": "software development lifecycle, system reliability, DevOps, and technical operations",
#         "tone_note": "technical, precise, structured with clear numbered steps",
#         "compliance_note": "SOC2 technical controls, ISO27001, change management policies",
#         "tools": "JIRA, GitHub, Jenkins, Kubernetes, Datadog",
#     },
#     "Product & Design": {
#         "focus": "product strategy, UX/UI design, roadmap planning, and user research",
#         "tone_note": "clear, user-centric, collaborative and iterative",
#         "compliance_note": "WCAG accessibility standards, privacy by design, data minimization",
#         "tools": "Figma, Jira, Confluence, Amplitude, Mixpanel",
#     },
#     "Marketing & Content": {
#         "focus": "brand management, content strategy, campaign execution, and lead generation",
#         "tone_note": "engaging, brand-aligned, clear calls to action",
#         "compliance_note": "GDPR for marketing lists, CAN-SPAM, FTC guidelines",
#         "tools": "HubSpot, Google Analytics, Mailchimp, Salesforce",
#     },
#     "Finance & Operations": {
#         "focus": "financial planning, accounting controls, budgeting, vendor management, and audit",
#         "tone_note": "precise, formal, data-driven and audit-ready",
#         "compliance_note": "GAAP/IFRS accounting standards, SOX compliance, tax regulations",
#         "tools": "QuickBooks, NetSuite, Expensify, Stripe",
#     },
#     "Partnership & Alliances": {
#         "focus": "partner ecosystem development, alliance strategy, and partner lifecycle management",
#         "tone_note": "collaborative, professional, mutually beneficial framing",
#         "compliance_note": "anti-bribery laws, revenue sharing compliance, data sharing agreements",
#         "tools": "Salesforce, PartnerStack, Confluence, Slack",
#     },
#     "IT & Internal Systems": {
#         "focus": "internal technology infrastructure, user support, system access, and IT governance",
#         "tone_note": "clear, step-by-step, accessible to both technical and non-technical staff",
#         "compliance_note": "ISO27001, NIST, SOC2 Type II, acceptable use policies",
#         "tools": "ServiceNow, Okta, Jamf, AWS, Azure",
#     },
#     "Platform & Infrastructure Operations": {
#         "focus": "cloud infrastructure, reliability engineering, capacity planning, and DevOps automation",
#         "tone_note": "highly technical, precise, SRE/DevOps best practices",
#         "compliance_note": "SOC2, ISO27001, CIS benchmarks, cloud security frameworks",
#         "tools": "AWS, Terraform, Kubernetes, Datadog, PagerDuty",
#     },
#     "Data & Analytics": {
#         "focus": "data governance, analytics pipelines, BI reporting, and data quality management",
#         "tone_note": "analytical, data-driven, precise definitions and measurable outcomes",
#         "compliance_note": "GDPR data processing requirements, CCPA, data retention laws, SOC2",
#         "tools": "Snowflake, dbt, Looker, Airflow, Python",
#     },
#     "QA & Testing": {
#         "focus": "quality assurance strategy, test automation, defect management, and release quality",
#         "tone_note": "methodical, detail-oriented, risk-aware and systematic",
#         "compliance_note": "ISO 9001 quality standards, accessibility testing (WCAG), security testing",
#         "tools": "Selenium, JIRA, TestRail, Postman, Jenkins",
#     },
#     "Security & Information Assurance": {
#         "focus": "cybersecurity, threat management, risk assessment, and information protection",
#         "tone_note": "authoritative, risk-focused, zero-ambiguity language",
#         "compliance_note": "ISO27001, SOC2 Type II, NIST CSF, CIS Controls, GDPR security requirements",
#         "tools": "Splunk, CrowdStrike, Tenable, AWS Security Hub",
#     },
# }


# # ============================================================
# # DOCUMENT LENGTH MAP
# # ============================================================
# DOCUMENT_LENGTH_MAP = {
#     # ── HR & People Operations ────────────────────────────────
#     "Offer Letter":                      {"min_pages": 1,  "max_pages": 1,  "target_words": 200},
#     "Employment Contract":               {"min_pages": 4,  "max_pages": 8,  "target_words": 4000},
#     "Employee Handbook":                 {"min_pages": 35, "max_pages": 40, "target_words": 13000},
#     "HR Policy Manual":                  {"min_pages": 20, "max_pages": 30, "target_words": 10000},
#     "Onboarding Checklist":              {"min_pages": 3,  "max_pages": 5,  "target_words": 2000},
#     "Performance Appraisal Form":        {"min_pages": 6,  "max_pages": 10, "target_words": 3500},
#     "Leave Policy Document":             {"min_pages": 8,  "max_pages": 12, "target_words": 4000},
#     "Code of Conduct":                   {"min_pages": 15, "max_pages": 25, "target_words": 7000},
#     "Exit Interview Form":               {"min_pages": 3,  "max_pages": 5,  "target_words": 1500},
#     "Training & Development Plan":       {"min_pages": 8,  "max_pages": 12, "target_words": 4000},
#     # ── Legal & Compliance ────────────────────────────────────
#     "Master Service Agreement (MSA)":    {"min_pages": 10, "max_pages": 20, "target_words": 6000},
#     "Non-Disclosure Agreement (NDA)":    {"min_pages": 3,  "max_pages": 6,  "target_words": 2000},
#     "Data Processing Agreement (DPA)":   {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "Privacy Policy":                    {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Terms of Service":                  {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "Compliance Audit Report":           {"min_pages": 10, "max_pages": 20, "target_words": 6000},
#     "Risk Assessment Report":            {"min_pages": 10, "max_pages": 18, "target_words": 5500},
#     "Intellectual Property Agreement":   {"min_pages": 4,  "max_pages": 8,  "target_words": 3000},
#     "Vendor Contract Template":          {"min_pages": 6,  "max_pages": 12, "target_words": 4000},
#     "Regulatory Compliance Checklist":   {"min_pages": 8,  "max_pages": 15, "target_words": 4500},
#     # ── Sales & Customer Facing ───────────────────────────────
#     "Sales Proposal Template":           {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Sales Playbook":                    {"min_pages": 15, "max_pages": 25, "target_words": 8000},
#     "Customer Onboarding Guide":         {"min_pages": 8,  "max_pages": 15, "target_words": 4500},
#     "Service Level Agreement (SLA)":     {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "Pricing Strategy Document":         {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Customer Case Study":               {"min_pages": 2,  "max_pages": 4,  "target_words": 1500},
#     "Sales Contract":                    {"min_pages": 4,  "max_pages": 8,  "target_words": 2500},
#     "CRM Usage Guidelines":              {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "Quarterly Sales Report":            {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Customer Feedback Report":          {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     # ── Engineering & Operations ──────────────────────────────
#     "Software Requirements Specification (SRS)": {"min_pages": 10, "max_pages": 20, "target_words": 6000},
#     "Technical Design Document (TDD)":   {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "API Documentation":                 {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "Deployment Guide":                  {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "Release Notes":                     {"min_pages": 2,  "max_pages": 5,  "target_words": 1500},
#     "System Architecture Document":      {"min_pages": 10, "max_pages": 20, "target_words": 6000},
#     "Incident Report":                   {"min_pages": 4,  "max_pages": 8,  "target_words": 2500},
#     "Root Cause Analysis (RCA)":         {"min_pages": 4,  "max_pages": 8,  "target_words": 2500},
#     "DevOps Runbook":                    {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "Change Management Log":             {"min_pages": 4,  "max_pages": 8,  "target_words": 2500},
#     # ── Product & Design ──────────────────────────────────────
#     "Product Requirements Document (PRD)": {"min_pages": 8, "max_pages": 15, "target_words": 5000},
#     "Product Roadmap":                   {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "Feature Specification Document":    {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "UX Research Report":                {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Wireframe Documentation":           {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "Design System Guide":               {"min_pages": 10, "max_pages": 20, "target_words": 6000},
#     "User Persona Document":             {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "A/B Testing Report":                {"min_pages": 4,  "max_pages": 8,  "target_words": 2500},
#     "Product Strategy Document":         {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "Competitive Analysis Report":       {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     # ── Marketing & Content ───────────────────────────────────
#     "Marketing Strategy Plan":           {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "Content Calendar":                  {"min_pages": 4,  "max_pages": 8,  "target_words": 2500},
#     "Brand Guidelines":                  {"min_pages": 10, "max_pages": 20, "target_words": 6000},
#     "SEO Strategy Document":             {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Campaign Performance Report":       {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "Social Media Strategy":             {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Email Marketing Plan":              {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Press Release Template":            {"min_pages": 1,  "max_pages": 2,  "target_words": 600},
#     "Market Research Report":            {"min_pages": 10, "max_pages": 18, "target_words": 5500},
#     "Lead Generation Plan":              {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     # ── Finance & Operations ──────────────────────────────────
#     "Annual Budget Plan":                {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "Financial Statement Report":        {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Expense Policy":                    {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "Invoice Template":                  {"min_pages": 2,  "max_pages": 6,  "target_words": 2500},
#     "Procurement Policy":                {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Revenue Forecast Report":           {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Cash Flow Statement":               {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "Vendor Payment Policy":             {"min_pages": 4,  "max_pages": 8,  "target_words": 2500},
#     "Cost Analysis Report":              {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Financial Risk Assessment":         {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     # ── Partnership & Alliances ───────────────────────────────
#     "Partnership Agreement":             {"min_pages": 6,  "max_pages": 12, "target_words": 4000},
#     "Memorandum of Understanding (MoU)": {"min_pages": 4,  "max_pages": 8,  "target_words": 2500},
#     "Channel Partner Agreement":         {"min_pages": 6,  "max_pages": 12, "target_words": 4000},
#     "Affiliate Program Agreement":       {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "Strategic Alliance Proposal":       {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Partner Onboarding Guide":          {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Joint Marketing Plan":              {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Revenue Sharing Agreement":         {"min_pages": 4,  "max_pages": 8,  "target_words": 2500},
#     "Partner Performance Report":        {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "NDA for Partners":                  {"min_pages": 3,  "max_pages": 6,  "target_words": 2000},
#     # ── IT & Internal Systems ─────────────────────────────────
#     "IT Policy Manual":                  {"min_pages": 20, "max_pages": 30, "target_words": 10000},
#     "Access Control Policy":             {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "IT Asset Management Policy":        {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Backup & Recovery Policy":          {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "Network Architecture Document":     {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "IT Support SOP":                    {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Disaster Recovery Plan":            {"min_pages": 10, "max_pages": 20, "target_words": 6000},
#     "Software License Tracking Log":     {"min_pages": 4,  "max_pages": 8,  "target_words": 2500},
#     "Internal System Audit Report":      {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "Hardware Procurement Policy":       {"min_pages": 4,  "max_pages": 8,  "target_words": 2500},
#     # ── Platform & Infrastructure Operations ─────────────────
#     "Infrastructure Architecture Document": {"min_pages": 10, "max_pages": 20, "target_words": 6000},
#     "Cloud Deployment Guide":            {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Capacity Planning Report":          {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Infrastructure Monitoring Plan":    {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Incident Response Plan":            {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "SLA for Infrastructure":            {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "Configuration Management Document": {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Uptime & Availability Report":      {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "Infrastructure Security Policy":    {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "Scalability Planning Document":     {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     # ── Data & Analytics ──────────────────────────────────────
#     "Data Governance Policy":            {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "Data Dictionary":                   {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "Business Intelligence (BI) Report": {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "KPI Dashboard Documentation":       {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Data Pipeline Documentation":       {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Data Quality Report":               {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "Analytics Strategy Document":       {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "Predictive Model Report":           {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Data Privacy Impact Assessment":    {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Reporting Standards Guide":         {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     # ── QA & Testing ──────────────────────────────────────────
#     "Test Plan Document":                {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "Test Case Template":                {"min_pages": 4,  "max_pages": 8,  "target_words": 2500},
#     "Test Strategy Document":            {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "Bug Report Template":               {"min_pages": 3,  "max_pages": 6,  "target_words": 2000},
#     "QA Checklist":                      {"min_pages": 4,  "max_pages": 8,  "target_words": 2500},
#     "Automation Test Plan":              {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Regression Test Report":            {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "UAT Document":                      {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Test Coverage Report":              {"min_pages": 5,  "max_pages": 10, "target_words": 3000},
#     "Performance Testing Report":        {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     # ── Security & Information Assurance ─────────────────────
#     "Information Security Policy":       {"min_pages": 10, "max_pages": 20, "target_words": 6000},
#     "Cybersecurity Risk Assessment":     {"min_pages": 10, "max_pages": 18, "target_words": 5500},
#     "Vulnerability Assessment Report":   {"min_pages": 8,  "max_pages": 15, "target_words": 5000},
#     "Penetration Testing Report":        {"min_pages": 10, "max_pages": 20, "target_words": 6000},
#     "Security Audit Report":             {"min_pages": 10, "max_pages": 18, "target_words": 5500},
#     "Data Classification Policy":        {"min_pages": 6,  "max_pages": 12, "target_words": 3500},
#     "Business Continuity Plan (BCP)":    {"min_pages": 12, "max_pages": 20, "target_words": 7000},
#     "Security Awareness Training Material": {"min_pages": 8, "max_pages": 15, "target_words": 5000},
#     # ── Default ───────────────────────────────────────────────
#     "_default":                          {"min_pages": 4,  "max_pages": 8,  "target_words": 3000},
# }

# # 1-page document types
# ONE_PAGE_DOCS = {"Offer Letter",  "Press Release Template"}


# # ============================================================
# # CONTENT CLEANER
# # ============================================================
# def clean_generated_content(content: str) -> str:
#     import re
#     content = re.sub(r'</?(?:div|span|p|br)[^>]*>', '', content)
#     content = re.sub(r'\n{4,}', '\n\n\n', content)
#     return content.strip()


# # ============================================================
# # PROMPT BUILDER
# # ============================================================
# def build_prompt(
#     industry,
#     department,
#     document_type,
#     question_answers,
#     sections,
#     doc_specs=None,
#     is_regeneration=False,
#     original_content="",
# ):
#     dept = DEPT_CONTEXT.get(department, {
#         "focus": f"{department} operations",
#         "tone_note": "professional and clear",
#         "compliance_note": "standard industry compliance",
#         "tools": f"Standard {department} tools",
#     })

#     doc_specs    = doc_specs or {}
#     length_map   = DOCUMENT_LENGTH_MAP.get(document_type, DOCUMENT_LENGTH_MAP["_default"])
#     min_pages    = doc_specs.get("min_pages")    or length_map["min_pages"]
#     max_pages    = doc_specs.get("max_pages")    or length_map["max_pages"]
#     target_words = doc_specs.get("target_words") or length_map["target_words"]

#     company_name    = question_answers.get("company_name", "the company")
#     company_size    = question_answers.get("company_size", "51-200")
#     primary_product = question_answers.get("primary_product", "SaaS platform")
#     target_market   = question_answers.get("target_market", "B2B")
#     specific_focus  = question_answers.get("specific_focus", "")
#     extra_context   = question_answers.get("additional_context", "") or question_answers.get("additional_ctx", "")
#     doc_title       = question_answers.get("document_title", document_type)
#     version         = question_answers.get("document_version", "1.0")
#     author          = question_answers.get("author_name", "")
#     approved_by     = question_answers.get("approved_by", "")

#     tools      = question_answers.get("tools_used", "")
#     tools_str  = ", ".join(tools) if isinstance(tools, list) else str(tools or dept.get("tools", ""))
#     compliance     = question_answers.get("compliance_requirements", "") or question_answers.get("compliance_req", "")
#     compliance_str = ", ".join(compliance) if isinstance(compliance, list) else str(compliance or dept["compliance_note"])

#     skip_keys = {
#         "company_name", "company_size", "primary_product", "target_market",
#         "tools_used", "specific_focus", "compliance_requirements", "compliance_req",
#         "geographic_locations", "tone_preference", "additional_context", "additional_ctx",
#         "document_title", "author_name", "approved_by", "document_version", "effective_date",
#     }
#     extra_answers = "\n".join(
#         f"  - {k.replace('_', ' ').title()}: " + (", ".join(v) if isinstance(v, list) else str(v))
#         for k, v in question_answers.items()
#         if k not in skip_keys and v and str(v) not in ("(select)", "", "None")
#     )

#     sections_block = ""
#     if sections:
#         sections_block = "REQUIRED SECTIONS:\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(sections))

#     focus_block = ""
#     if specific_focus:
#         focus_block += f"\nSPECIFIC FOCUS: {specific_focus}"
#     if extra_context:
#         focus_block += f"\nADDITIONAL CONTEXT: {extra_context}"
#     if extra_answers:
#         focus_block += f"\nUSER DETAILS:\n{extra_answers}"

#     # ── 1-PAGE DOCUMENTS ──────────────────────────────────────
#     if document_type in ONE_PAGE_DOCS or (min_pages == 1 and max_pages == 1):
#         candidate  = question_answers.get("candidate_name", "") or question_answers.get("recipient_name", "")
#         job_title  = question_answers.get("job_title", "") or question_answers.get("position", "")
#         salary     = question_answers.get("salary", "") or question_answers.get("compensation", "")
#         start_date = question_answers.get("start_date", "") or question_answers.get("joining_date", "") or question_answers.get("effective_date", "")

#         return f"""Write a professional {document_type} for {company_name}.

# STRICT RULE: Write EXACTLY 150-200 words. No more, no less.
# FORMAT: Plain text letter ONLY.
# NO markdown. NO ## headers. NO bullet points. NO tables. NO sections.
# STRUCTURE: Date → Greeting → 2-3 short paragraphs → Closing → Signature line.
# STOP after signature/acceptance line.

# DETAILS:
# - Company: {company_name}
# - Recipient: {candidate or '[Candidate Name]'}
# - Role: {job_title or '[Job Title]'}
# - Compensation: {salary or '[Salary]'}
# - Start Date: {start_date or '[Start Date]'}
# - Offer valid: 72 hours
# {focus_block}

# Write the {document_type} now (150-200 words ONLY):"""

#     # ── REGENERATION ──────────────────────────────────────────
#     if is_regeneration and original_content:
#         return f"""Enhance this {document_type} for {company_name}.
# Keep all sections. Improve quality. Add compliance refs ({compliance_str}).
# Target: {target_words:,} words.

# ORIGINAL:
# {original_content[:3000]}

# Write enhanced version now:"""

#     # ── STANDARD DOCUMENT ─────────────────────────────────────
#     return f"""You are a senior enterprise documentation specialist.
# Write a COMPLETE {document_type} for {company_name}.

# COMPANY:
# - Name: {company_name} ({company_size} employees)
# - Industry: {industry} | Product: {primary_product} | Market: {target_market}
# - Department: {department} — {dept['focus']}
# - Tools: {tools_str}
# - Compliance: {compliance_str}

# DOCUMENT INFO:
# - Title: {doc_title}
# - Version: {version}
# - Author: {author or department + ' Team'}
# - Approver: {approved_by or 'Management'}

# {sections_block}
# {focus_block}

# RULES:
# 1. Use "{company_name}" everywhere — NEVER "the company"
# 2. NO placeholders: NO [Insert X], NO TBD, NO [Date]
# 3. Real numbers, specific dates, named tools
# 4. Tone: {dept['tone_note']}
# 5. Compliance: {compliance_str}
# 6. Format: ## sections, ### subsections, **bold** terms, tables for data
# 7. Start: document header (title, dept, version, date, author, approver)
# 8. End: Version History table

# MANDATORY: Write ALL sections — {min_pages}-{max_pages} pages (~{target_words:,} words)
# Each section minimum 250 words. Full detail. No summaries.
# Do NOT stop until ALL sections + Version History are complete.

# Write the COMPLETE {document_type.upper()} for {company_name.upper()} now:"""


# # ============================================================
# # MAIN GENERATION FUNCTION
# # ============================================================
# def generate_document(
#     industry,
#     department,
#     document_type,
#     question_answers,
#     is_regeneration=False,
#     original_content="",
# ):
#     logger.info(f"Generating: {document_type} | {department} | {question_answers.get('company_name', 'N/A')}")

#     sections  = []
#     doc_specs = {}
#     try:
#         from services.template_repository import get_template_by_type
#         from services.questionnaire_repository import get_questionnaire_by_type

#         template = get_template_by_type(document_type, department)
#         if template:
#             sections = template.get("structure", {}).get("sections", [])

#         questionnaire = get_questionnaire_by_type(department, document_type)
#         if questionnaire:
#             for q in questionnaire.get("questions", []):
#                 if q.get("id") == "_document_specs":
#                     doc_specs = q.get("document_specs", {})
#                     break
#     except Exception as e:
#         logger.warning(f"DB load failed: {e}")

#     length_map   = DOCUMENT_LENGTH_MAP.get(document_type, DOCUMENT_LENGTH_MAP["_default"])
#     merged       = {**length_map, **{k: v for k, v in doc_specs.items() if v}}
#     min_page     = merged.get("min_pages", 1)
#     max_page     = merged.get("max_pages", 8)
#     target_words = merged.get("target_words", 3000)

#     logger.info(f"Specs: {min_page}-{max_page} pages | {target_words} words")

#     prompt = build_prompt(
#         industry, department, document_type,
#         question_answers, sections, merged,
#         is_regeneration, original_content,
#     )

#     endpoint    = os.getenv("AZURE_LLM_ENDPOINT", "").rstrip("/")
#     api_key     = (
#         os.getenv("AZURE_OPENAI_LLM_KEY")
#         or os.getenv("AZURE_OPENAI_API_KEY")
#         or os.getenv("OPENAI_API_KEY")
#     )
#     api_version = os.getenv("AZURE_LLM_API_VERSION", "2025-01-01-preview")
#     deployment  = (
#         os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI")
#         or os.getenv("AZURE_OPENAI_DEPLOYMENT")
#         or "gpt-4.1-mini"
#     )

#     if not endpoint or not api_key:
#         raise ValueError("Missing AZURE_LLM_ENDPOINT or AZURE_OPENAI_LLM_KEY in .env")

#     est_tokens = int(target_words * 1.35)
#     is_one_page = document_type in ONE_PAGE_DOCS or (min_page == 1 and max_page == 1)

#     if is_one_page:
#         max_tokens  = 300
#         temperature = 0.1
#     elif max_page <= 3:
#         max_tokens  = min(est_tokens + 500, 3000)
#         temperature = 0.4
#     elif max_page <= 10:
#         max_tokens  = min(est_tokens + 2000, 10000)
#         temperature = 0.5
#     elif max_page <= 20:
#         max_tokens  = min(est_tokens + 3000, 14000)
#         temperature = 0.5
#     else:
#         max_tokens  = 16000
#         temperature = 0.5

#     if is_regeneration:
#         max_tokens  = min(max_tokens + 2000, 16000)
#         temperature = max(temperature - 0.1, 0.1)

#     logger.info(f"max_tokens={max_tokens} | temperature={temperature}")

#     try:
#         from openai import AzureOpenAI

#         # client = AzureOpenAI(
#         #     azure_endpoint=endpoint,
#         #     api_key=api_key,
#         #     api_version=api_version,
#         # )
#         import httpx
#         client = AzureOpenAI(
#             azure_endpoint=endpoint,
#             api_key=api_key,
#             api_version=api_version,
#             http_client=httpx.Client(),
#         )

#         if is_one_page:
#             system_msg = (
#                 "You are a professional business writer. "
#                 "Write EXACTLY 150-200 words. Plain text ONLY. "
#                 "NO markdown. NO headers. NO tables. NO bullets. "
#                 "STOP after signature line."
#             )
#         else:
#             system_msg = (
#                 "You are a senior enterprise documentation specialist. "
#                 "Write COMPLETE, DETAILED, PROFESSIONAL documents. "
#                 "EVERY section must have minimum 250 words with tables, examples, procedures. "
#                 "NEVER write short summaries. NEVER stop early. "
#                 "Write ALL sections completely. End with Version History table."
#             )

#         if is_regeneration:
#             system_msg += " REGENERATION: Significantly improve quality and completeness."

#         response = client.chat.completions.create(
#             model=deployment,
#             messages=[
#                 {"role": "system", "content": system_msg},
#                 {"role": "user",   "content": prompt},
#             ],
#             temperature=temperature,
#             max_tokens=max_tokens,
#         )

#         part1  = clean_generated_content(response.choices[0].message.content)
#         finish = response.choices[0].finish_reason
#         words  = len(part1.split())
#         logger.info(f"Part 1: {words} words | finish: {finish}")

#         # Continuation for cut-off documents
#         if finish == "length" and not is_one_page and words < target_words * 0.75:
#             logger.info("Generating Part 2 continuation...")
#             try:
#                 cont = client.chat.completions.create(
#                     model=deployment,
#                     messages=[
#                         {"role": "system", "content": system_msg},
#                         {"role": "user",   "content": prompt},
#                         {"role": "assistant", "content": part1},
#                         {"role": "user",   "content": f"Continue from where you stopped. Write ALL remaining sections. Current: {words} words, target: {target_words}. Start immediately:"},
#                     ],
#                     temperature=temperature,
#                     max_tokens=max_tokens,
#                 )
#                 part2 = clean_generated_content(cont.choices[0].message.content)
#                 full  = part1 + "\n\n" + part2
#                 logger.info(f"Total: {len(full.split())} words after continuation")
#                 return full
#             except Exception as e:
#                 logger.warning(f"Continuation failed: {e}")

#         return part1

#     except ImportError:
#         raise ImportError("openai not installed. Run: pip install openai>=1.0.0")
#     except Exception as e:
#         logger.error(f"Azure OpenAI failed: {e}", exc_info=True)
#         raise RuntimeError(f"Azure OpenAI call failed: {e}") from e




