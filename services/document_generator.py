"""
Document Generator — Uses openai SDK directly (no LangChain wrapper).
Avoids the 'proxies' keyword argument bug in older langchain-openai versions.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# DEPARTMENT CONTEXT
# ============================================================
DEPT_CONTEXT = {
    "HR & People Operations": {
        "focus": "people management, talent acquisition, employee lifecycle, culture, and HR compliance",
        "tone_note": "empathetic, people-first, clear and inclusive language",
        "compliance_note": "employment law, GDPR for employee data, equal opportunity regulations",
    },
    "Legal & Compliance": {
        "focus": "legal risk management, regulatory compliance, contracts, and corporate governance",
        "tone_note": "precise, formal, unambiguous legal language",
        "compliance_note": "GDPR, SOC2, ISO27001, local employment law, CCPA, anti-bribery laws",
    },
    "Sales & Customer-Facing": {
        "focus": "revenue generation, customer relationships, deal management, and customer retention",
        "tone_note": "confident, persuasive, customer-centric language",
        "compliance_note": "GDPR for customer data, fair trade practices, CRM data privacy",
    },
    "Engineering & Operations": {
        "focus": "software development lifecycle, system reliability, DevOps, and technical operations",
        "tone_note": "technical, precise, structured with clear numbered steps",
        "compliance_note": "SOC2 technical controls, ISO27001, change management policies",
    },
    "Product & Design": {
        "focus": "product strategy, UX/UI design, roadmap planning, and user research",
        "tone_note": "clear, user-centric, collaborative and iterative",
        "compliance_note": "WCAG accessibility standards, privacy by design, data minimization",
    },
    "Marketing & Content": {
        "focus": "brand management, content strategy, campaign execution, and lead generation",
        "tone_note": "engaging, brand-aligned, clear calls to action",
        "compliance_note": "GDPR for marketing lists, CAN-SPAM, FTC guidelines",
    },
    "Finance & Operations": {
        "focus": "financial planning, accounting controls, budgeting, vendor management, and audit",
        "tone_note": "precise, formal, data-driven and audit-ready",
        "compliance_note": "GAAP/IFRS accounting standards, SOX compliance, tax regulations",
    },
    "Partnership & Alliances": {
        "focus": "partner ecosystem development, alliance strategy, and partner lifecycle management",
        "tone_note": "collaborative, professional, mutually beneficial framing",
        "compliance_note": "anti-bribery laws, revenue sharing compliance, data sharing agreements",
    },
    "IT & Internal Systems": {
        "focus": "internal technology infrastructure, user support, system access, and IT governance",
        "tone_note": "clear, step-by-step, accessible to both technical and non-technical staff",
        "compliance_note": "ISO27001, NIST, SOC2 Type II, acceptable use policies",
    },
    "Platform & Infrastructure Operation": {
        "focus": "cloud infrastructure, reliability engineering, capacity planning, and DevOps automation",
        "tone_note": "highly technical, precise, SRE/DevOps best practices",
        "compliance_note": "SOC2, ISO27001, CIS benchmarks, cloud security frameworks",
    },
    "Data & Analytics": {
        "focus": "data governance, analytics pipelines, BI reporting, and data quality management",
        "tone_note": "analytical, data-driven, precise definitions and measurable outcomes",
        "compliance_note": "GDPR data processing requirements, CCPA, data retention laws, SOC2",
    },
    "QA & Testing": {
        "focus": "quality assurance strategy, test automation, defect management, and release quality",
        "tone_note": "methodical, detail-oriented, risk-aware and systematic",
        "compliance_note": "ISO 9001 quality standards, accessibility testing (WCAG), security testing",
    },
    "Security & Information Assurance": {
        "focus": "cybersecurity, threat management, risk assessment, and information protection",
        "tone_note": "authoritative, risk-focused, zero-ambiguity language",
        "compliance_note": "ISO27001, SOC2 Type II, NIST CSF, CIS Controls, GDPR security requirements",
    },
}

# ============================================================
# DOC TYPE INSTRUCTIONS
# ============================================================
DOC_TYPE_INSTRUCTIONS = {
    "SOP": "Write numbered step-by-step procedures (min 5 sub-steps each). Include WHO, WHAT, HOW, WHEN for every step. Add decision points with IF/THEN logic. Include a Roles & Responsibilities table. Reference actual tools in each step.",
    "Policy": "Use mandatory language: must/shall/is prohibited. Define scope precisely. Include compliance checklist, violation consequences (tiered), exceptions process, and reference specific laws.",
    "Proposal": "Include Executive Summary, quantified problem, phased solution, ROI analysis, Risk Register (5+ risks), budget breakdown by category, success KPIs with baseline/target, implementation timeline table.",
    "SOW": "Include explicit IN-SCOPE and OUT-OF-SCOPE lists. Deliverables table with acceptance criteria. RACI matrix. Payment schedule tied to milestones. Change request process. List 8+ assumptions.",
    "Incident Report": "Chronological timeline with HH:MM timestamps. Quantify impact (users, revenue, SLA breach). 5-Why Root Cause Analysis (5 levels deep). Action items table with Owner/Due Date/Success Criteria. Lessons Learned by People/Process/Technology.",
    "FAQ": "Write 18-20 Q&A pairs organized by category. Each answer must be complete and self-contained. Include escalation path. Mix basic and advanced questions written from end-user perspective.",
    "Runbook": "Prerequisites checklist. Numbered steps with exact commands/UI paths. Expected output after EACH step. Troubleshooting table: Symptom|Cause|Fix. Rollback procedure. Time estimates per section.",
    "Playbook": "5+ distinct scenarios with dedicated plays. Each play: Trigger→Assessment→Actions→Escalation→Resolution. Success metrics per play. Common mistakes to avoid. Decision tree for complex scenarios.",
    "RCA": "Problem statement (precise, quantified). Full 5-Why chain. Fishbone analysis (People/Process/Technology/Environment). SMART action items table. Effectiveness validation plan.",
    "SLA": "Service definition (in-scope AND excluded). SLA Metrics table with exact numbers. Priority matrix P1-P4 with response AND resolution times. Credit formula. Escalation matrix with contact roles.",
    "Change Management": "Change Request form template. Risk scoring matrix (Likelihood×Impact). Approval authority table by change type. Rollback trigger criteria. Communication plan template. Post-implementation review checklist.",
    "Handbook": "Table of Contents. 10+ substantive chapters. Policy + procedure + guidance integrated per chapter. Checklists and quick-reference tables throughout. FAQ at end of major chapters. Version history.",
}

LENGTH_GUIDE = {
    "SOP": "3,500–5,000 words", "Policy": "2,500–4,000 words",
    "Proposal": "3,000–4,500 words", "SOW": "2,500–4,000 words",
    "Incident Report": "2,000–3,000 words", "FAQ": "2,500–3,500 words",
    "Runbook": "3,000–4,500 words", "Playbook": "3,500–5,000 words",
    "RCA": "2,500–3,500 words", "SLA": "2,500–4,000 words",
    "Change Management": "2,500–4,000 words", "Handbook": "5,000–8,000 words",
}

# ============================================================
# PROMPT BUILDER
# ============================================================
def build_prompt(industry, department, document_type, question_answers, sections):
    dept = DEPT_CONTEXT.get(department, {
        "focus": f"{department} operations",
        "tone_note": "professional and clear",
        "compliance_note": "standard industry compliance",
    })
    doc_instr = DOC_TYPE_INSTRUCTIONS.get(document_type, "Write a comprehensive professional document with detailed, actionable content for every section.")

    company_name    = question_answers.get("company_name", "the company")
    company_size    = question_answers.get("company_size", "Medium (51-200)")
    primary_product = question_answers.get("primary_product", "SaaS platform")
    target_market   = question_answers.get("target_market", "B2B")
    specific_focus  = question_answers.get("specific_focus", "")
    extra_context   = question_answers.get("additional_context", "")
    tone_pref       = question_answers.get("tone_preference", "Professional & Friendly")
    geo_locations   = question_answers.get("geographic_locations", "Global / Remote-first")

    tools = question_answers.get("tools_used", "")
    tools_str = ", ".join(tools) if isinstance(tools, list) else str(tools or f"Standard {department} tools")

    compliance = question_answers.get("compliance_requirements", "")
    compliance_str = ", ".join(compliance) if isinstance(compliance, list) else str(compliance or dept["compliance_note"])

    # Collect remaining answers
    skip = {"company_name","company_size","primary_product","target_market","tools_used",
            "specific_focus","compliance_requirements","geographic_locations","tone_preference","additional_context"}
    extra = "\n".join(
        f"  • {k.replace('q_','').replace('_',' ').title()}: {', '.join(v) if isinstance(v,list) else v}"
        for k, v in question_answers.items()
        if k not in skip and v and v != "(select)"
    ) or "  • No additional inputs"

    sections_str = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(sections)) if sections else \
        "  1. Purpose\n  2. Scope\n  3. Definitions\n  4. Roles & Responsibilities\n  5. Procedures\n  6. Tools & Systems\n  7. Compliance\n  8. Exceptions\n  9. Review\n  10. Approval"

    length = LENGTH_GUIDE.get(document_type, "3,000–4,500 words")

    return f"""You are a senior enterprise documentation consultant with 15+ years of experience writing {document_type} documents for {industry} SaaS companies, specializing in the {department} function.

You write immediately usable documents — specific, actionable, and tailored to the exact company. You NEVER use placeholder text like "[Insert here]" or "TBD".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPANY PROFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Company       : {company_name}
Size          : {company_size}
Industry      : {industry}
Product       : {primary_product}
Market        : {target_market}
Locations     : {geo_locations}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCUMENT SPECIFICATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Type          : {document_type}
Department    : {department}
Dept Focus    : {dept['focus']}
Specific Topic: {specific_focus or f'Comprehensive {department} {document_type}'}
Tone          : {tone_pref} ({dept['tone_note']})
Target Length : {length}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOOLS & SYSTEMS (reference these in procedures)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{tools_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPLIANCE REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{compliance_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADDITIONAL USER INPUTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{extra}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXTRA CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{extra_context or 'None provided'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCUMENT SECTIONS (cover in this order)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{sections_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{document_type.upper()} SPECIFIC REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{doc_instr}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NON-NEGOTIABLE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Use "{company_name}" throughout — NEVER write "the company" or "[Company Name]"
2. NEVER use "[Insert X]", "TBD", or any placeholder text
3. Reference actual tools ({tools_str}) in procedures — not generic placeholders
4. Include real numbers: timeframes, percentages, thresholds
5. Scale content appropriately for {company_size}
6. Format: ## main sections, ### subsections, **bold** key terms, tables where appropriate
7. End with a Version History table: Version | Date | Author | Changes
8. Reach the target length of {length}

GENERATE THE COMPLETE {document_type.upper()} FOR {company_name.upper()} NOW:
"""


# ============================================================
# MAIN FUNCTION — uses openai SDK directly
# ============================================================
def generate_document(industry, department, document_type, question_answers):
    # Get template sections from DB
    sections = []
    try:
        from services.template_repository import get_template_by_type
        template = get_template_by_type(document_type, department)
        if template:
            sections = template.get("structure", {}).get("sections", [])
    except Exception:
        pass

    prompt = build_prompt(industry, department, document_type, question_answers, sections)

    # Load credentials
    endpoint   = os.getenv("AZURE_LLM_ENDPOINT", "").rstrip("/")
    api_key    = (os.getenv("AZURE_OPENAI_LLM_KEY")
                  or os.getenv("AZURE_OPENAI_API_KEY")
                  or os.getenv("OPENAI_API_KEY"))
    api_version = os.getenv("AZURE_LLM_API_VERSION", "2025-01-01-preview")
    deployment  = (os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI")
                   or os.getenv("AZURE_OPENAI_DEPLOYMENT")
                   or os.getenv("AZURE_LLM_DEPLOYMENT")
                   or "gpt-4.1-mini")

    if not endpoint or not api_key:
        raise ValueError(
            "Missing Azure credentials in .env\n"
            "Need: AZURE_LLM_ENDPOINT and AZURE_OPENAI_LLM_KEY"
        )

    # Use openai SDK directly — avoids langchain 'proxies' bug
    try:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )

        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior enterprise documentation consultant. "
                        "You write professional, detailed, immediately usable documents. "
                        "You never use placeholder text. You always use the exact company name provided."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.65,
            max_tokens=3000,
        )

        return response.choices[0].message.content

    except ImportError:
        raise ImportError("openai package not installed. Run: pip install openai")
    except Exception as e:
        raise RuntimeError(
            f"Azure OpenAI call failed: {str(e)}\n"
            f"Endpoint  : {endpoint}\n"
            f"Deployment: {deployment}\n"
            f"Version   : {api_version}"
        ) from e

# ------------------------------------------------------------------------------------

# """
# Document Generator — Uses openai SDK directly (no LangChain wrapper).
# Avoids the 'proxies' keyword argument bug in older langchain-openai versions.
# """
# import os
# from dotenv import load_dotenv

# load_dotenv()

# # ============================================================
# # DEPARTMENT CONTEXT
# # ============================================================
# DEPT_CONTEXT = {
#     "HR & People Operations": {
#         "focus": "people management, talent acquisition, employee lifecycle, culture, and HR compliance",
#         "tone_note": "empathetic, people-first, clear and inclusive language",
#         "compliance_note": "employment law, GDPR for employee data, equal opportunity regulations",
#     },
#     "Legal & Compliance": {
#         "focus": "legal risk management, regulatory compliance, contracts, and corporate governance",
#         "tone_note": "precise, formal, unambiguous legal language",
#         "compliance_note": "GDPR, SOC2, ISO27001, local employment law, CCPA, anti-bribery laws",
#     },
#     "Sales & Customer-Facing": {
#         "focus": "revenue generation, customer relationships, deal management, and customer retention",
#         "tone_note": "confident, persuasive, customer-centric language",
#         "compliance_note": "GDPR for customer data, fair trade practices, CRM data privacy",
#     },
#     "Engineering & Operations": {
#         "focus": "software development lifecycle, system reliability, DevOps, and technical operations",
#         "tone_note": "technical, precise, structured with clear numbered steps",
#         "compliance_note": "SOC2 technical controls, ISO27001, change management policies",
#     },
#     "Product & Design": {
#         "focus": "product strategy, UX/UI design, roadmap planning, and user research",
#         "tone_note": "clear, user-centric, collaborative and iterative",
#         "compliance_note": "WCAG accessibility standards, privacy by design, data minimization",
#     },
#     "Marketing & Content": {
#         "focus": "brand management, content strategy, campaign execution, and lead generation",
#         "tone_note": "engaging, brand-aligned, clear calls to action",
#         "compliance_note": "GDPR for marketing lists, CAN-SPAM, FTC guidelines",
#     },
#     "Finance & Operations": {
#         "focus": "financial planning, accounting controls, budgeting, vendor management, and audit",
#         "tone_note": "precise, formal, data-driven and audit-ready",
#         "compliance_note": "GAAP/IFRS accounting standards, SOX compliance, tax regulations",
#     },
#     "Partnership & Alliances": {
#         "focus": "partner ecosystem development, alliance strategy, and partner lifecycle management",
#         "tone_note": "collaborative, professional, mutually beneficial framing",
#         "compliance_note": "anti-bribery laws, revenue sharing compliance, data sharing agreements",
#     },
#     "IT & Internal Systems": {
#         "focus": "internal technology infrastructure, user support, system access, and IT governance",
#         "tone_note": "clear, step-by-step, accessible to both technical and non-technical staff",
#         "compliance_note": "ISO27001, NIST, SOC2 Type II, acceptable use policies",
#     },
#     "Platform & Infrastructure Operation": {
#         "focus": "cloud infrastructure, reliability engineering, capacity planning, and DevOps automation",
#         "tone_note": "highly technical, precise, SRE/DevOps best practices",
#         "compliance_note": "SOC2, ISO27001, CIS benchmarks, cloud security frameworks",
#     },
#     "Data & Analytics": {
#         "focus": "data governance, analytics pipelines, BI reporting, and data quality management",
#         "tone_note": "analytical, data-driven, precise definitions and measurable outcomes",
#         "compliance_note": "GDPR data processing requirements, CCPA, data retention laws, SOC2",
#     },
#     "QA & Testing": {
#         "focus": "quality assurance strategy, test automation, defect management, and release quality",
#         "tone_note": "methodical, detail-oriented, risk-aware and systematic",
#         "compliance_note": "ISO 9001 quality standards, accessibility testing (WCAG), security testing",
#     },
#     "Security & Information Assurance": {
#         "focus": "cybersecurity, threat management, risk assessment, and information protection",
#         "tone_note": "authoritative, risk-focused, zero-ambiguity language",
#         "compliance_note": "ISO27001, SOC2 Type II, NIST CSF, CIS Controls, GDPR security requirements",
#     },
# }

# # ============================================================
# # DOC TYPE INSTRUCTIONS
# # ============================================================
# DOC_TYPE_INSTRUCTIONS = {
#     "SOP": "Write numbered step-by-step procedures (min 5 sub-steps each). Include WHO, WHAT, HOW, WHEN for every step. Add decision points with IF/THEN logic. Include a Roles & Responsibilities table. Reference actual tools in each step.",
#     "Policy": "Use mandatory language: must/shall/is prohibited. Define scope precisely. Include compliance checklist, violation consequences (tiered), exceptions process, and reference specific laws.",
#     "Proposal": "Include Executive Summary, quantified problem, phased solution, ROI analysis, Risk Register (5+ risks), budget breakdown by category, success KPIs with baseline/target, implementation timeline table.",
#     "SOW": "Include explicit IN-SCOPE and OUT-OF-SCOPE lists. Deliverables table with acceptance criteria. RACI matrix. Payment schedule tied to milestones. Change request process. List 8+ assumptions.",
#     "Incident Report": "Chronological timeline with HH:MM timestamps. Quantify impact (users, revenue, SLA breach). 5-Why Root Cause Analysis (5 levels deep). Action items table with Owner/Due Date/Success Criteria. Lessons Learned by People/Process/Technology.",
#     "FAQ": "Write 18-20 Q&A pairs organized by category. Each answer must be complete and self-contained. Include escalation path. Mix basic and advanced questions written from end-user perspective.",
#     "Runbook": "Prerequisites checklist. Numbered steps with exact commands/UI paths. Expected output after EACH step. Troubleshooting table: Symptom|Cause|Fix. Rollback procedure. Time estimates per section.",
#     "Playbook": "5+ distinct scenarios with dedicated plays. Each play: Trigger→Assessment→Actions→Escalation→Resolution. Success metrics per play. Common mistakes to avoid. Decision tree for complex scenarios.",
#     "RCA": "Problem statement (precise, quantified). Full 5-Why chain. Fishbone analysis (People/Process/Technology/Environment). SMART action items table. Effectiveness validation plan.",
#     "SLA": "Service definition (in-scope AND excluded). SLA Metrics table with exact numbers. Priority matrix P1-P4 with response AND resolution times. Credit formula. Escalation matrix with contact roles.",
#     "Change Management": "Change Request form template. Risk scoring matrix (Likelihood×Impact). Approval authority table by change type. Rollback trigger criteria. Communication plan template. Post-implementation review checklist.",
#     "Handbook": "Table of Contents. 10+ substantive chapters. Policy + procedure + guidance integrated per chapter. Checklists and quick-reference tables throughout. FAQ at end of major chapters. Version history.",
# }

# LENGTH_GUIDE = {
#     "SOP": "3,500–5,000 words", "Policy": "2,500–4,000 words",
#     "Proposal": "3,000–4,500 words", "SOW": "2,500–4,000 words",
#     "Incident Report": "2,000–3,000 words", "FAQ": "2,500–3,500 words",
#     "Runbook": "3,000–4,500 words", "Playbook": "3,500–5,000 words",
#     "RCA": "2,500–3,500 words", "SLA": "2,500–4,000 words",
#     "Change Management": "2,500–4,000 words", "Handbook": "5,000–8,000 words",
# }

# # ============================================================
# # PROMPT BUILDER
# # ============================================================
# def build_prompt(industry, department, document_type, question_answers, sections):
#     dept = DEPT_CONTEXT.get(department, {
#         "focus": f"{department} operations",
#         "tone_note": "professional and clear",
#         "compliance_note": "standard industry compliance",
#     })
#     doc_instr = DOC_TYPE_INSTRUCTIONS.get(document_type, "Write a comprehensive professional document with detailed, actionable content for every section.")

#     company_name    = question_answers.get("company_name", "the company")
#     company_size    = question_answers.get("company_size", "Medium (51-200)")
#     primary_product = question_answers.get("primary_product", "SaaS platform")
#     target_market   = question_answers.get("target_market", "B2B")
#     specific_focus  = question_answers.get("specific_focus", "")
#     extra_context   = question_answers.get("additional_context", "")
#     tone_pref       = question_answers.get("tone_preference", "Professional & Friendly")
#     geo_locations   = question_answers.get("geographic_locations", "Global / Remote-first")

#     tools = question_answers.get("tools_used", "")
#     tools_str = ", ".join(tools) if isinstance(tools, list) else str(tools or f"Standard {department} tools")

#     compliance = question_answers.get("compliance_requirements", "")
#     compliance_str = ", ".join(compliance) if isinstance(compliance, list) else str(compliance or dept["compliance_note"])

#     # Collect remaining answers
#     skip = {"company_name","company_size","primary_product","target_market","tools_used",
#             "specific_focus","compliance_requirements","geographic_locations","tone_preference","additional_context"}
#     extra = "\n".join(
#         f"  • {k.replace('q_','').replace('_',' ').title()}: {', '.join(v) if isinstance(v,list) else v}"
#         for k, v in question_answers.items()
#         if k not in skip and v and v != "(select)"
#     ) or "  • No additional inputs"

#     sections_str = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(sections)) if sections else \
#         "  1. Purpose\n  2. Scope\n  3. Definitions\n  4. Roles & Responsibilities\n  5. Procedures\n  6. Tools & Systems\n  7. Compliance\n  8. Exceptions\n  9. Review\n  10. Approval"

#     length = LENGTH_GUIDE.get(document_type, "3,000–4,500 words")

#     return f"""You are a senior enterprise documentation consultant with 15+ years of experience writing {document_type} documents for {industry} SaaS companies, specializing in the {department} function.

# You write immediately usable documents — specific, actionable, and tailored to the exact company. You NEVER use placeholder text like "[Insert here]" or "TBD".

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMPANY PROFILE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Company       : {company_name}
# Size          : {company_size}
# Industry      : {industry}
# Product       : {primary_product}
# Market        : {target_market}
# Locations     : {geo_locations}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DOCUMENT SPECIFICATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Type          : {document_type}
# Department    : {department}
# Dept Focus    : {dept['focus']}
# Specific Topic: {specific_focus or f'Comprehensive {department} {document_type}'}
# Tone          : {tone_pref} ({dept['tone_note']})
# Target Length : {length}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TOOLS & SYSTEMS (reference these in procedures)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# {tools_str}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMPLIANCE REQUIREMENTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# {compliance_str}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADDITIONAL USER INPUTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# {extra}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXTRA CONTEXT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# {extra_context or 'None provided'}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DOCUMENT SECTIONS (cover in this order)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# {sections_str}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# {document_type.upper()} SPECIFIC REQUIREMENTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# {doc_instr}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# NON-NEGOTIABLE RULES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. Use "{company_name}" throughout — NEVER write "the company" or "[Company Name]"
# 2. NEVER use "[Insert X]", "TBD", or any placeholder text
# 3. Reference actual tools ({tools_str}) in procedures — not generic placeholders
# 4. Include real numbers: timeframes, percentages, thresholds
# 5. Scale content appropriately for {company_size}
# 6. Format: ## main sections, ### subsections, **bold** key terms, tables where appropriate
# 7. End with a Version History table: Version | Date | Author | Changes
# 8. Reach the target length of {length}

# GENERATE THE COMPLETE {document_type.upper()} FOR {company_name.upper()} NOW:
# """


# # ============================================================
# # MAIN FUNCTION — uses openai SDK directly
# # ============================================================
# def generate_document(industry, department, document_type, question_answers):
#     # Get template sections from DB
#     sections = []
#     try:
#         from services.template_repository import get_template_by_type
#         template = get_template_by_type(document_type, department)
#         if template:
#             sections = template.get("structure", {}).get("sections", [])
#     except Exception:
#         pass

#     prompt = build_prompt(industry, department, document_type, question_answers, sections)

#     # Load credentials
#     endpoint   = os.getenv("AZURE_LLM_ENDPOINT", "").rstrip("/")
#     api_key    = (os.getenv("AZURE_OPENAI_LLM_KEY")
#                   or os.getenv("AZURE_OPENAI_API_KEY")
#                   or os.getenv("OPENAI_API_KEY"))
#     api_version = os.getenv("AZURE_LLM_API_VERSION", "2025-01-01-preview")
#     deployment  = (os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI")
#                    or os.getenv("AZURE_OPENAI_DEPLOYMENT")
#                    or os.getenv("AZURE_LLM_DEPLOYMENT")
#                    or "gpt-4.1-mini")

#     if not endpoint or not api_key:
#         raise ValueError(
#             "Missing Azure credentials in .env\n"
#             "Need: AZURE_LLM_ENDPOINT and AZURE_OPENAI_LLM_KEY"
#         )

#     # Use openai SDK directly — avoids langchain 'proxies' bug
#     try:
#         from openai import AzureOpenAI

#         client = AzureOpenAI(
#             azure_endpoint=endpoint,
#             api_key=api_key,
#             api_version=api_version,
#         )

#         response = client.chat.completions.create(
#             model=deployment,
#             messages=[
#                 {
#                     "role": "system",
#                     "content": (
#                         "You are a senior enterprise documentation consultant. "
#                         "You write professional, detailed, immediately usable documents. "
#                         "You never use placeholder text. You always use the exact company name provided."
#                     ),
#                 },
#                 {"role": "user", "content": prompt},
#             ],
#             temperature=0.65,
#             max_tokens=3000,
#         )

#         return response.choices[0].message.content

#     except ImportError:
#         raise ImportError("openai package not installed. Run: pip install openai")
#     except Exception as e:
#         raise RuntimeError(
#             f"Azure OpenAI call failed: {str(e)}\n"
#             f"Endpoint  : {endpoint}\n"
#             f"Deployment: {deployment}\n"
#             f"Version   : {api_version}"
#         ) from e
    
#--------------------------------------------------------------------------------


# """
# Document Generator
# - Fetches template sections from PostgreSQL (seeded from content.json)
# - Fetches questions from PostgreSQL (seeded from Question_Answer.json)
# - Builds enhanced LangChain prompt from user's question_answers
# - Calls Azure OpenAI to generate document
# """
# import os
# import json
# from dotenv import load_dotenv
# from services.template_repository import get_template_by_type
# from services.questionnaire_repository import get_questionnaire_by_type

# load_dotenv()


# def build_prompt(
#     industry: str,
#     department: str,
#     document_type: str,
#     question_answers: dict,
#     sections: list,
#     questions: list,
# ) -> str:
#     """Build the full LangChain-style prompt from template + user answers."""

#     # ── Extract common answers ──
#     company_name    = question_answers.get("company_name", "the company")
#     company_size    = question_answers.get("company_size", "Medium")
#     primary_product = question_answers.get("primary_product", "SaaS platform")
#     target_market   = question_answers.get("target_market", "B2B")
#     tools_used      = question_answers.get("tools_used", [])
#     specific_focus  = question_answers.get("specific_focus", "")
#     compliance_reqs = question_answers.get("compliance_requirements", [])
#     geo_locations   = question_answers.get("geographic_locations", "")
#     tone_preference = question_answers.get("tone_preference", "Professional & Friendly")
#     extra_context   = question_answers.get("additional_context", "")

#     # ── Format tools ──
#     tools_str = ""
#     if tools_used:
#         if isinstance(tools_used, list):
#             tools_str = ", ".join(tools_used)
#         else:
#             tools_str = str(tools_used)

#     # ── Format compliance ──
#     compliance_str = ""
#     if compliance_reqs:
#         if isinstance(compliance_reqs, list):
#             compliance_str = ", ".join(compliance_reqs)
#         else:
#             compliance_str = str(compliance_reqs)

#     # ── Format sections ──
#     sections_formatted = "\n".join([f"  {i+1}. {s}" for i, s in enumerate(sections)])

#     # ── Collect any doc-type or dept specific answers ──
#     extra_answers = []
#     skip_keys = {
#         "company_name", "company_size", "primary_product", "target_market",
#         "tools_used", "specific_focus", "compliance_requirements",
#         "geographic_locations", "tone_preference", "additional_context"
#     }
#     for k, v in question_answers.items():
#         if k not in skip_keys and v:
#             label = k.replace("q_", "").replace("_", " ").title()
#             extra_answers.append(f"  - {label}: {v}")
#     extra_str = "\n".join(extra_answers) if extra_answers else "  None provided"

#     prompt = f"""You are an expert technical writer specializing in SaaS enterprise documentation.
# Generate a comprehensive, professional {document_type} document for the {department} department.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMPANY CONTEXT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Company Name      : {company_name}
# Company Size      : {company_size}
# Primary Product   : {primary_product}
# Target Market     : {target_market}
# Industry          : {industry}
# Locations         : {geo_locations if geo_locations else 'Not specified'}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DOCUMENT CONTEXT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Department        : {department}
# Document Type     : {document_type}
# Specific Focus    : {specific_focus if specific_focus else f'{department} {document_type}'}
# Tone              : {tone_preference}
# Compliance        : {compliance_str if compliance_str else 'Standard best practices'}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TOOLS & SYSTEMS TO REFERENCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# {tools_str if tools_str else 'Standard industry tools'}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADDITIONAL CONTEXT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# {extra_context if extra_context else 'None'}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADDITIONAL INPUTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# {extra_str}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REQUIRED DOCUMENT SECTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# {sections_formatted}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GENERATION INSTRUCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. Use "{company_name}" instead of generic "Company" references throughout.
# 2. Reference the actual tools listed above in relevant sections.
# 3. Tailor content specifically to {department} department processes.
# 4. Include {compliance_str if compliance_str else 'general'} compliance considerations where relevant.
# 5. Use a {tone_preference} writing style throughout.
# 6. Make content specific, actionable, and relevant to a {company_size} SaaS company.
# 7. Include realistic examples, metrics, and timelines where appropriate.
# 8. Each section must have substantive content — no placeholder text.
# 9. Format the document clearly with section headers using markdown (## for sections).
# 10. Generate the complete document now:
# """
#     return prompt


# def generate_document(
#     industry: str,
#     department: str,
#     document_type: str,
#     question_answers: dict,
# ) -> str:
#     """
#     Main function:
#     1. Fetch template from DB
#     2. Fetch questionnaire from DB
#     3. Build prompt
#     4. Call Azure OpenAI
#     5. Return generated content
#     """

#     # ── 1. Get template sections from DB ──
#     template = get_template_by_type(document_type, department)
#     if template:
#         sections = template.get("structure", {}).get("sections", [])
#     else:
#         # Fallback default sections
#         sections = [
#             "Purpose", "Scope", "Definitions", "Roles & Responsibilities",
#             "Procedures", "Tools & Systems Used", "Compliance & Policies",
#             "Review & Revision", "Approval"
#         ]

#     # ── 2. Get questions from DB (for context, already answered by user) ──
#     questionnaire = get_questionnaire_by_type(document_type, department)
#     questions = questionnaire.get("questions", []) if questionnaire else []

#     # ── 3. Build prompt ──
#     prompt = build_prompt(
#         industry=industry,
#         department=department,
#         document_type=document_type,
#         question_answers=question_answers,
#         sections=sections,
#         questions=questions,
#     )

#     # ── 4. Call Azure OpenAI ──
#     from langchain_openai import AzureChatOpenAI
#     from langchain.schema import HumanMessage

#     llm = AzureChatOpenAI(
#         azure_endpoint=os.getenv("AZURE_LLM_ENDPOINT"),
#         api_key=os.getenv("AZURE_OPENAI_LLM_KEY"),
#         api_version=os.getenv("AZURE_LLM_API_VERSION"),
#         azure_deployment=os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI"),
#         temperature=0.7,
#         max_tokens=4000,
#     )

#     response = llm.invoke([HumanMessage(content=prompt)])
#     return response.content

#-------------------------------------------------------------------------------------

# import json
# import re
# from typing import Dict, Any, List

# from services.langchain_service import generate_document_with_langchain
# from services.template_repository import get_template_by_type
# from services.questionnaire_repository import get_questionnaire_by_type


# # --------------------------------------------------
# # Utility: Clean Markdown Output
# # --------------------------------------------------

# def clean_markdown_output(text: str) -> str:
#     text = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
#     text = re.sub(r"```$", "", text.strip())
#     return text.strip()


# # --------------------------------------------------
# # Extract Sections from Template Structure
# # --------------------------------------------------

# def extract_sections(structure: Dict[str, Any]) -> List[str]:
#     sections = []
#     raw_sections = structure.get("sections", [])

#     for section in raw_sections:
#         if isinstance(section, str):
#             sections.append(section)
#         elif isinstance(section, dict):
#             for parent, children in section.items():
#                 sections.append(parent)
#                 if isinstance(children, list):
#                     sections.extend(children)

#     return sections


# # --------------------------------------------------
# # Build Prompt for a Single Section
# # --------------------------------------------------

# def build_section_prompt(
#     industry: str,
#     department: str,
#     document_type: str,
#     section_name: str,
#     question_answers: Dict[str, Any],
# ) -> str:
#     answers_text = json.dumps(question_answers, indent=2)

#     return f"""You are a senior SaaS documentation expert.

# Generate ONLY the section titled: "{section_name}"

# Document Type: {document_type}
# Department: {department}
# Industry: {industry}

# Business Context (answers provided by user):
# {answers_text}

# Instructions:
# - Write ONLY this section. Do not write other sections.
# - Be detailed, structured, and professional.
# - Use clean Markdown formatting.
# - Do NOT wrap output in ```markdown``` code blocks.
# - Do NOT include the document title or department header.
# """


# # --------------------------------------------------
# # Main Document Generator
# # --------------------------------------------------

# def generate_document(
#     industry: str,
#     department: str,
#     document_type: str,
#     question_answers: Dict[str, Any],
# ) -> str:

#     # 1. Fetch Template
#     template = get_template_by_type(document_type)
#     if not template:
#         raise ValueError(
#             f"No template found for document type: '{document_type}'. "
#             f"Please create a template first via POST /templates/"
#         )

#     # 2. Fetch Questionnaire (optional — used for context only)
#     questionnaire = get_questionnaire_by_type(document_type)
#     # questionnaire is optional — document can still generate without it

#     # 3. Extract Sections from Template
#     sections = extract_sections(template["structure"])

#     if not sections:
#         raise ValueError(
#             f"Template for '{document_type}' has no sections defined. "
#             f"Make sure your template structure has a 'sections' key."
#         )

#     # 4. Build Document Header
#     final_document = f"# {document_type}\n\n"
#     final_document += f"**Department:** {department} | **Industry:** {industry}\n\n"
#     final_document += "---\n\n"

#     # 5. Generate Each Section via LLM
#     for section in sections:
#         prompt = build_section_prompt(
#             industry=industry,
#             department=department,
#             document_type=document_type,
#             section_name=section,
#             question_answers=question_answers,
#         )

#         section_content = generate_document_with_langchain(prompt)
#         section_content = clean_markdown_output(section_content)

#         final_document += f"## {section}\n\n"
#         final_document += section_content + "\n\n---\n\n"

#     return final_document.strip()

#-------------------------------------------------------
# import json
# import re
# from typing import Dict, Any, List
# from services.langchain_service import generate_document_with_langchain
# from services.template_repository import get_template_by_type
# from services.questionnaire_repository import get_questionnaire_by_type


# # --------------------------------------------------
# # Utility: Clean Markdown Output
# # --------------------------------------------------

# def clean_markdown_output(text: str) -> str:
#     if text.startswith("```"):
#         text = re.sub(r"^```[a-zA-Z]*", "", text)
#         text = re.sub(r"```$", "", text)
#     return text.strip()


# # --------------------------------------------------
# # Prompt Builder for Single Section
# # --------------------------------------------------

# def build_section_prompt(
#     industry: str,
#     department: str,
#     document_type: str,
#     section_name: str,
#     questionnaire_answers: Dict[str, Any],
# ) -> str:

#     answers_text = json.dumps(questionnaire_answers, indent=2)

#     prompt = f"""
# You are a senior SaaS documentation expert.

# Generate ONLY the section titled:

# {section_name}

# For a {document_type} document in the {department} department
# within the {industry} industry.

# Business Context:
# {answers_text}

# Instructions:
# - Write only this section.
# - Do not repeat other sections.
# - Be detailed and professional.
# - Use clean Markdown.
# - Do NOT include ```markdown tags.
# - Do NOT include document title.
# """

#     return prompt


# # --------------------------------------------------
# # Extract Sections from Template
# # --------------------------------------------------

# def extract_sections(template_structure: Dict[str, Any]) -> List[str]:
#     sections = []

#     raw_sections = template_structure.get("sections", [])

#     for section in raw_sections:
#         if isinstance(section, str):
#             sections.append(section)

#         elif isinstance(section, dict):
#             for parent, children in section.items():
#                 sections.append(parent)
#                 sections.extend(children)

#     return sections


# # --------------------------------------------------
# # Main Document Generator (Section-wise)
# # --------------------------------------------------

# def generate_document(
#     industry: str,
#     department: str,
#     document_type: str,
#     question_answers: Dict[str, Any],
# ) -> str:

#     # 1️⃣ Fetch Template
#     template = get_template_by_type(document_type)
#     if not template:
#         raise ValueError(f"Template not found: {document_typea}")

#     # 2️⃣ Fetch Questionnaire
#     questionnaire = get_questionnaire_by_type(document_type)
#     if not questionnaire:
#         raise ValueError(f"Questionnaire not found: {document_type}")

#     # 3️⃣ Extract Sections
#     sections = extract_sections(template["structure"])

#     final_document = f"# {document_type}\n\n"
#     final_document += f"## {department} Department\n\n---\n\n"

#     # 4️⃣ Generate Each Section Separately
#     for section in sections:
#         prompt = build_section_prompt(
#             industry=industry,
#             department=department,
#             document_type=document_type,
#             section_name=section,
#             questionnaire_answers=question_answers,
#         )

#         section_content = generate_document_with_langchain(prompt)
#         section_content = clean_markdown_output(section_content)

#         final_document += f"## {section}\n\n"
#         final_document += section_content + "\n\n---\n\n"

#     return final_document.strip()
