"""
Document Generator — Uses openai SDK directly (no LangChain wrapper).
Avoids the 'proxies' keyword argument bug in older langchain-openai versions.

UPDATED:
  • All 13 departments × 10 doc types fully mapped in DOC_TYPE_INSTRUCTIONS + LENGTH_GUIDE
  • Enhanced prompt with chain-of-thought scaffolding for higher accuracy
  • Zero placeholder / TBD tolerance enforced at prompt level
"""

import os
from dotenv import load_dotenv
from utils.logger import setup_logger

load_dotenv()

logger = setup_logger(__name__)

def clean_generated_content(content: str) -> str:
    """Remove any HTML tags leaked into generated markdown content."""
    import re
    # Remove HTML tags
    content = re.sub(r'</?div[^>]*>', '', content)
    content = re.sub(r'</?span[^>]*>', '', content)
    content = re.sub(r'</?p[^>]*>', '', content)
    content = re.sub(r'<br\s*/?>', '\n', content)
    # Clean multiple blank lines
    content = re.sub(r'\n{4,}', '\n\n\n', content)
    return content.strip()



# ============================================================
# DEPARTMENT CONTEXT  (13 departments)
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
    "Sales & Customer Facing": {
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
    "Platform & Infrastructure Operations": {
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
# DOC TYPE INSTRUCTIONS  — ALL 130 types (13 depts × 10 types)
# ============================================================
DOC_TYPE_INSTRUCTIONS = {

    # ── HR & People Operations ────────────────────────────────────────────
    "Offer Letter": (
        "Write a concise 1-page offer letter (150-200 words ONLY). Include: "
        "(1) Greeting with candidate name, (2) Job title & start date, "
        "(3) Base salary only (NO benefits table), (4) Offer expiry (72 hours), "
        "(5) Simple acceptance instruction with signature line. "
        "Format: Professional letter, plain text, NO bullet points, NO tables, NO sections. "
        "Be warm but brief. Count words carefully - MUST stay under 200 words."
    ),
    "Employment Contract": (
        "Draft a comprehensive bilateral employment contract. Include: (1) Parties clause with full "
        "legal entity names, (2) Commencement date and probation period terms (length, extension "
        "conditions, performance review criteria), (3) Duties & responsibilities schedule, "
        "(4) Compensation & benefits schedule with exact figures, (5) Working hours, overtime policy, "
        "and flexible-work provisions, (6) Confidentiality & IP assignment clause, (7) Non-solicitation "
        "clause (duration and geographic scope), (8) Termination conditions — notice periods by "
        "seniority level, (9) Grievance & disciplinary procedure reference, (10) Governing law clause. "
        "Use mandatory legal language: 'shall', 'must', 'is required to'."
    ),
    "Employee Handbook": (
        "Write a COMPLETE Employee Handbook (13,000-15,000 words, 35-40 pages). "
        "Use EXACTLY this heading format:\n"
        "# PART 1: INTRODUCTION\n"
        "# PART 2: EMPLOYMENT POLICIES\n"
        "# PART 3: WORK POLICIES\n"
        "# PART 4: COMPENSATION & BENEFITS\n"
        "# PART 5: TIME-OFF & LEAVE POLICIES\n"
        "# PART 6: CONDUCT & COMPLIANCE\n"
        "# PART 7: HEALTH, SAFETY & SECURITY\n"
        "# PART 8: APPENDICES\n"
        "Each ## subsection must be 200-500 words. WRITE ALL PARTS COMPLETELY:\n"
        "Generate SECTION BY SECTION with full detail and professional formatting:"
        "PART 1 — INTRODUCTORY SECTIONS (Pages 1-4):"
        "  • Cover page with company name, document version, effective date"
        "  • Table of Contents (detailed, numbered)"
        "  • Welcome Message from CEO (300-400 words)"
        "  • Company Overview (history, mission, vision, values, culture) (500+ words)"
        "  • Equal Employment Opportunity & Diversity Policy (300+ words)"
        "PART 2 — EMPLOYMENT POLICIES (Pages 5-12):"
        "  • Employment Categories & Classification (200+ words)"
        "  • Recruitment & Hiring Process (300+ words)"
        "  • Onboarding & New Employee Orientation (300+ words)"
        "  • Probation & Confirmation Policy (250+ words)"
        "  • Employee Records & Confidentiality (200+ words)"
        "PART 3 — WORK POLICIES (Pages 13-18):"
        "  • Work Hours & Schedule (300+ words with examples)"
        "  • Attendance & Punctuality (250+ words with consequences)"
        "  • Remote Work & Hybrid Work Policy (400+ words detailed)"
        "  • Flexible Work Arrangements (250+ words)"
        "PART 4 — COMPENSATION & BENEFITS (Pages 19-24):"
        "  • Compensation Policy Framework (300+ words)"
        "  • Salary & Payroll Procedures (300+ words with tables)"
        "  • Health Insurance & Benefits (400+ words)"
        "  • Employee Bonuses & Incentives (250+ words)"
        "  • Other Benefits (retirement, wellness, etc.) (300+ words)"
        "PART 5 — TIME-OFF POLICIES (Pages 25-28):"
        "  • Vacation & Annual Leave Policy (300+ words with accrual table)"
        "  • Sick Leave Policy (250+ words)"
        "  • Public Holidays (200+ words with holiday schedule)"
        "  • Maternity/Paternity & Other Leaves (300+ words)"
        "PART 6 — PERFORMANCE & DEVELOPMENT (Pages 29-32):"
        "  • Performance Management Process (400+ words step-by-step)"
        "  • Annual Appraisal Cycle (300+ words with timeline)"
        "  • Career Development & Training (300+ words)"
        "  • Promotion & Career Advancement (250+ words with criteria)"
        "PART 7 — CONDUCT & DISCIPLINE (Pages 33-36):"
        "  • Code of Conduct (500+ words professional standards)"
        "  • Ethical Business Practices (300+ words)"
        "  • Workplace Behavior & Professionalism (300+ words)"
        "  • Dress Code & Appearance (200+ words with examples)"
        "  • Disciplinary Action Framework (400+ words with progressive steps)"
        "  • Grievance & Complaint Process (300+ words with flowchart)"
        "PART 8 — COMPLIANCE & SECURITY (Pages 37-40):"
        "  • Data Privacy & IT Security Policy (400+ words)"
        "  • Confidentiality & Non-Disclosure (300+ words)"
        "  • Intellectual Property Rights (250+ words)"
        "  • Health & Safety Standards (300+ words)"
        "  • Exit & Offboarding Process (250+ words with checklist)"
        "APPENDICES:"
        "  • FAQ Section (all common questions answered)"
        "  • Glossary of Terms"
        "  • Employee Acknowledgment Form"
        "  • Revision History & Document Control"
        "CRITICAL REQUIREMENTS:"
        "- Each section must be detailed, professional, and substantive"
        "- Use real company examples and policies (no placeholders)"
        "- Include numbered procedures, checklists, tables, policy matrices"
        "- Write 250-500 words per major section (NOT summaries)"
        "- Professional business tone throughout"
        "- Total: 13,000-15,000 words across 70+ sections on 35-40 pages"
        "- Ensure document flows logically section by section"
    ),
    "HR Policy Manual": (
        "Produce a formal HR Policy Manual. For every policy include: Policy Number, Effective Date, "
        "Owner, Scope, Policy Statement, Procedures (numbered steps), Roles & Responsibilities table, "
        "Exceptions process, Non-compliance consequences (tiered: verbal warning → written warning → "
        "termination), and Review cycle. Mandatory policies: Recruitment & Selection, Onboarding, "
        "Performance Management, Disciplinary Action, Grievance Handling, Leave Management, "
        "Remote Work, Anti-Harassment & Discrimination, Data Privacy for Employee Data, "
        "and Offboarding."
    ),
    "Onboarding Checklist": (
        "Create a multi-phase onboarding checklist covering: Pre-Arrival (IT setup, access provisioning, "
        "desk/equipment), Day 1 (welcome meeting, office tour, system logins, HR paperwork), "
        "Week 1 (team introductions, tool training, 1:1 with manager), 30-Day (first performance "
        "conversation, goal setting, culture integration check), 60-Day (project ownership, feedback "
        "session), 90-Day (probation review, career path discussion). Each item must include: "
        "Owner role, Estimated time, Completion checkbox, and Notes column. Format as a structured "
        "table per phase."
    ),
    "Performance Appraisal Form": (
        "Design a complete performance appraisal form. Sections: (1) Employee information block, "
        "(2) Review period and cycle type (annual/mid-year/probation), (3) Goal achievement table — "
        "Goal | Target | Actual | Score (1-5) | Comments, (4) Competency ratings (min 8 competencies "
        "with behavioural anchors per score), (5) Manager narrative — strengths, development areas, "
        "key wins, (6) Employee self-assessment section, (7) Development plan table — Skill Gap | "
        "Action | Timeline | Support Needed, (8) Overall rating scale with calibration guide, "
        "(9) Promotion/merit recommendation, (10) Dual-signature and HR acknowledgment blocks."
    ),
    "Leave Policy Document": (
        "Write a detailed leave policy. For every leave type include: Eligibility criteria, "
        "Entitlement days/weeks, Accrual method, Carry-forward rules, Notice requirements, "
        "Documentation required, Pay treatment during leave, Return-to-work process, and Manager "
        "approval workflow. Leave types to cover: Annual Leave, Sick Leave, Parental (Maternity, "
        "Paternity, Adoption), Bereavement, Study/Exam Leave, Jury Duty, Public Holidays, "
        "Unpaid Leave, and Emergency/Compassionate Leave. Include a Leave Request Flow diagram "
        "described in text, and an escalation matrix."
    ),
    "Code of Conduct": (
        "Write an authoritative Code of Conduct. Sections must include: (1) CEO/Leadership message, "
        "(2) Our Values — 5-6 values with behavioural descriptions, (3) Conflicts of Interest — "
        "definition, disclosure process, prohibited activities, (4) Confidentiality & Information "
        "Security, (5) Anti-Harassment, Anti-Discrimination and Workplace Respect, "
        "(6) Fair Competition & Anti-Bribery, (7) Social Media & Public Communications, "
        "(8) Use of Company Assets & Resources, (9) Reporting Violations — anonymous hotline, "
        "non-retaliation guarantee, (10) Disciplinary Consequences — tiered matrix, "
        "(11) Annual acknowledgment requirement. Use 'must', 'is prohibited', 'is required'."
    ),
    "Exit Interview Form": (
        "Create a thorough exit interview form with: (1) Employee and departure details block, "
        "(2) Reason for leaving — categorised checkboxes + open text, (3) Role satisfaction ratings "
        "(1-5 scale: workload, compensation, growth, management, culture, tools), (4) Manager "
        "relationship assessment, (5) Company strengths — 3 open questions, (6) Areas for improvement "
        "— 3 open questions, (7) Likelihood to recommend score (NPS 0-10) with comment box, "
        "(8) Rehire eligibility section, (9) Knowledge transfer confirmation checklist, "
        "(10) Interviewer notes and HR action items table. Format for both digital and printed use."
    ),
    "Training & Development Plan": (
        "Build a structured Training & Development Plan. Include: (1) Skills gap assessment framework, "
        "(2) Individual Development Plan (IDP) template with 90-day / 6-month / 12-month milestones, "
        "(3) Learning catalogue table — Course Name | Provider | Format | Duration | Cost | "
        "Completion Target | Linked Competency, (4) Mandatory vs elective training matrix by role, "
        "(5) Manager coaching cadence, (6) Budget allocation by department, (7) ROI measurement "
        "framework (pre/post assessment, behavioural change indicators), (8) Certification tracking "
        "table, (9) Succession planning tie-in section."
    ),

    # ── Legal & Compliance ────────────────────────────────────────────────
    "Master Service Agreement (MSA)": (
        "Draft a complete MSA. Clauses required: Definitions, Scope of Services, Fees & Payment Terms "
        "(net-30/60, late fees, disputed invoices process), Intellectual Property ownership and license "
        "grants, Confidentiality (mutual, 3-year tail), Data Protection & GDPR compliance obligations, "
        "Representations & Warranties (both parties), Limitation of Liability (cap formula), "
        "Indemnification obligations, Term & Termination for cause/convenience (30/60/90-day notice), "
        "Dispute Resolution (escalation → mediation → arbitration), Governing Law & Jurisdiction, "
        "Force Majeure, and Entire Agreement clause. Exhibit placeholders: SOW, DPA, SLA."
    ),
    "Non-Disclosure Agreement (NDA)": (
        "Write a bilateral NDA covering: (1) Definition of Confidential Information (broad + carve-outs), "
        "(2) Obligations of Receiving Party — permitted use, need-to-know standard, security measures, "
        "(3) Exclusions from confidentiality — 4 standard carve-outs, (4) Compelled disclosure process, "
        "(5) Return/destruction of information upon request, (6) Term — agreement duration AND "
        "survival period (minimum 3 years post-termination), (7) Remedies clause (injunctive relief), "
        "(8) No license / no partnership / no obligation to disclose clause, (9) Signature blocks "
        "with entity name, signatory name, title, date."
    ),
    "Data Processing Agreement (DPA)": (
        "Draft a GDPR-compliant DPA. Required sections: Definitions (Controller, Processor, Sub-processor, "
        "Data Subject, Personal Data), Subject-Matter and Duration, Nature and Purpose of Processing, "
        "Categories of Personal Data and Data Subjects, Processor Obligations (Article 28 compliance — "
        "instructions only, confidentiality, security measures, sub-processor rules, Data Subject rights "
        "assistance, deletion/return, audit cooperation), Controller Obligations, Sub-processors "
        "(list + approval process), International Transfers (SCCs, adequacy decisions), Security "
        "Measures Schedule (technical and organisational), Liability Allocation, and Governing Law."
    ),
    "Privacy Policy": (
        "Write a GDPR + CCPA compliant Privacy Policy. Sections: (1) Who We Are & Contact Details, "
        "(2) Data We Collect — categorised table: Personal Data type | Source | Legal Basis | "
        "Retention Period, (3) How We Use Your Data — purpose-by-purpose explanation, (4) Legal Bases "
        "(consent, legitimate interests, contract, legal obligation), (5) Cookies & Tracking, "
        "(6) Third-Party Sharing — named categories of recipients, (7) International Transfers & "
        "safeguards, (8) Your Rights — GDPR 8 rights + CCPA rights with exercise instructions, "
        "(9) Retention Schedule, (10) Children's Privacy (under 13/16), (11) Policy Updates process, "
        "(12) Contact & Complaints (DPA contact details)."
    ),
    "Terms of Service": (
        "Write comprehensive Terms of Service (ToS). Sections: Acceptance mechanism, Eligibility, "
        "Account registration and security, License grant (scope, restrictions, termination), "
        "Acceptable Use Policy with prohibited conduct list, Intellectual Property ownership, "
        "User Content — license grant to company, responsibility, removal rights, Fees & Billing "
        "(subscription terms, auto-renewal, refunds, price changes), Service Availability & SLA "
        "reference, Disclaimers of Warranty, Limitation of Liability (cap and exclusions), "
        "Indemnification by User, DMCA/IP infringement process, Termination and effect of "
        "termination, Dispute Resolution (governing law, arbitration clause, class action waiver), "
        "General provisions (entire agreement, severability, waiver)."
    ),
    "Compliance Audit Report": (
        "Write a formal compliance audit report. Structure: Executive Summary with audit scope "
        "and overall rating, Audit Methodology (framework used, evidence collected, sampling approach), "
        "Scope and Objectives, Regulatory Framework applicable, Findings table — Control ID | "
        "Requirement | Evidence Reviewed | Finding | Severity (Critical/High/Medium/Low) | "
        "Recommendation, Detailed Findings section (one page per critical/high finding with root cause), "
        "Management Response table — Finding ID | Management Comment | Remediation Owner | Due Date, "
        "Remediation Roadmap with timeline, Conclusion & Auditor Sign-off."
    ),
    "Risk Assessment Report": (
        "Produce a comprehensive Risk Assessment Report. Include: (1) Executive Summary, "
        "(2) Risk Assessment Methodology (ISO 31000 or NIST RMF reference), (3) Risk Register table — "
        "Risk ID | Category | Description | Likelihood (1-5) | Impact (1-5) | Risk Score | "
        "Risk Owner | Current Controls | Residual Risk | Treatment Plan | Due Date, "
        "(4) Heat Map description (narrative of 5×5 matrix quadrants), (5) Top 10 Risks deep-dive "
        "(one paragraph each), (6) Risk Treatment Plans with SMART actions, (7) Monitoring & Review "
        "cadence, (8) Escalation Thresholds, (9) Residual Risk Acceptance sign-off table."
    ),
    "Intellectual Property Agreement": (
        "Draft an IP Assignment Agreement covering: (1) Background IP vs Foreground IP distinction, "
        "(2) Full assignment clause — all IP created during employment/engagement assigned to company, "
        "(3) Works for Hire declaration (US) / equivalent clause (other jurisdictions), "
        "(4) Moral Rights waiver, (5) Pre-existing IP schedule — employee lists IP retained, "
        "(6) Cooperation obligations post-termination (sign documents, assist applications), "
        "(7) License-back to employee for personal pre-existing IP used in work, (8) Injunctive "
        "relief clause, (9) Compensation for assignment (if required by local law), "
        "(10) Governing law and jurisdiction."
    ),
    "Vendor Contract Template": (
        "Create a standard Vendor Contract Template. Sections: Vendor details & onboarding checklist, "
        "Services/Goods description (Exhibit A), Pricing & Payment Schedule, Delivery milestones "
        "and acceptance criteria, Warranties and representations (vendor), Performance SLAs with "
        "penalty/credit mechanism, Insurance requirements (types, minimum coverage amounts), "
        "Audit rights, Confidentiality, Data Security requirements (if vendor processes company data), "
        "Termination — for convenience (60 days), for cause (30 days), for insolvency (immediate), "
        "Transition assistance obligation, Liability cap, Indemnification, and Governing Law."
    ),
    "Regulatory Compliance Checklist": (
        "Build a detailed Regulatory Compliance Checklist. For each regulation include: Regulation name, "
        "Applicability trigger, Key requirements checklist (10+ items per regulation), Evidence "
        "required, Review frequency, Responsible owner, and RAG status. Regulations to cover: "
        "GDPR, CCPA, SOC2 Type II, ISO 27001, Employment Law (jurisdiction-specific), AML/Anti-Bribery, "
        "Accessibility (WCAG 2.1), and any sector-specific regulation. Add an annual compliance "
        "calendar and escalation matrix for non-compliance findings."
    ),

    # ── Sales & Customer Facing ───────────────────────────────────────────
    "Sales Proposal Template": (
        "Write a winning sales proposal template. Sections: (1) Executive Summary — customer pain, "
        "proposed solution, investment, and expected ROI in one page, (2) About Us — company "
        "credentials, customer logos, key metrics, (3) Understanding Your Challenge — mirrored "
        "back to the prospect's stated needs, (4) Proposed Solution — feature table with "
        "benefit-per-feature mapping, (5) Implementation Timeline — phased table with milestones, "
        "(6) Pricing Options — Good/Better/Best table with ROI calculation, (7) Case Studies × 2 "
        "(quantified outcomes), (8) Risk Mitigation — how proposal reduces prospect's risk, "
        "(9) Terms & Conditions summary, (10) Next Steps — clear CTA with owner and date."
    ),
    "Sales Playbook": (
        "Build a comprehensive Sales Playbook with 6+ plays. Each play must contain: "
        "Trigger (signal that activates this play), Objective, ICP Profile (firmographic + "
        "behavioural), Messaging Framework (value prop, differentiators, objection-handling table "
        "with 8+ objections), Discovery Question Bank (10+ questions by category), Email/Call "
        "sequence (5+ touch multi-channel), Qualification Criteria (MEDDIC or BANT checklist), "
        "Exit Criteria (advance or disqualify), Success KPIs. Include a Competitive Battle Card "
        "section (2+ competitors) and a common mistakes / anti-patterns table."
    ),
    "Customer Onboarding Guide": (
        "Write a Customer Onboarding Guide. Structure: Welcome section with success definition, "
        "Onboarding phases table — Phase | Activities | Owner | Duration | Success Metric, "
        "Step-by-step setup instructions (with exact UI paths and commands where relevant), "
        "Integration checklist, Training schedule and resource links, Admin configuration guide, "
        "Go-Live checklist, Post-Go-Live support model (who to contact, SLA), Escalation path, "
        "Success metrics dashboard description (KPIs the CSM will track), and a 30/60/90-day "
        "milestone review template."
    ),
    "Service Level Agreement (SLA)": (
        "Draft a complete SLA. Sections: Service definition (in-scope and explicitly excluded), "
        "SLA Metrics table — Metric | Definition | Target | Measurement Method | Reporting Frequency, "
        "Availability commitment (e.g. 99.9% monthly), Priority Matrix — P1/P2/P3/P4 with "
        "Response Time AND Resolution Time AND Escalation Path per priority, Service Credit formula "
        "(% credit per breach, monthly cap), Reporting obligations (format, frequency, recipient), "
        "Exclusions from SLA (scheduled maintenance, customer-caused incidents, force majeure), "
        "Review and renegotiation process, Escalation matrix with named roles (not names), "
        "Definitions glossary."
    ),
    "Pricing Strategy Document": (
        "Write a Pricing Strategy Document. Include: (1) Pricing Philosophy and principles, "
        "(2) Market & Competitive Analysis — pricing positioning matrix, (3) Cost Structure Analysis "
        "(COGS, CAC, LTV/CAC ratio targets), (4) Pricing Model options evaluated "
        "(usage-based, seat-based, flat, tiered, freemium) with pros/cons, (5) Recommended Pricing "
        "Architecture — tier table with features, limits, and price per tier, (6) Discounting Policy "
        "— authority matrix by discount level, (7) Pricing for different segments/geos, "
        "(8) Price Change Management Process, (9) Success Metrics (ACV, ARR, NRR, churn impact), "
        "(10) Annual review cadence."
    ),
    "Customer Case Study": (
        "Write a compelling B2B customer case study. Structure: Headline (outcome-led), "
        "Customer snapshot (industry, size, geography, ICP match), Challenge section "
        "(before-state: pain points, failed alternatives, urgency), Solution section "
        "(why chosen, implementation highlights, time-to-value), Results section "
        "(minimum 3 quantified outcomes with % or $ improvement, comparison to baseline), "
        "Direct quote from champion (job title, not name), and Next Steps / Expansion. "
        "Include a sidebar summary box: Challenge | Solution | Results bullets. "
        "Write in narrative storytelling style, third person."
    ),
    "Sales Contract": (
        "Draft a standard Sales Contract / Order Form. Sections: Parties and effective date, "
        "Subscription/Product details table — SKU | Description | Quantity | Unit Price | "
        "Total, Contract term (start, end, auto-renewal clause), Payment terms "
        "(invoice timing, due dates, accepted methods, late fees), Usage restrictions, "
        "Reference to MSA / ToS, Accepted signatures block, Order Form Exhibits "
        "(technical specs, support tier selected), Change Order process, and "
        "Early Termination Fee schedule."
    ),
    "CRM Usage Guidelines": (
        "Write CRM Usage Guidelines. Include: (1) Purpose and CRM vision, "
        "(2) Data Entry Standards — required fields by record type (Lead/Contact/Account/Opportunity/Activity), "
        "(3) Lead Management Process — lifecycle stages, qualification criteria, handoff rules, "
        "(4) Opportunity Management — stage definitions, exit criteria, probability table, "
        "required fields per stage, (5) Activity Logging Standards — what to log, when, format, "
        "(6) Data Quality Rules — deduplication, field validation, update frequency, "
        "(7) Reporting Standards — dashboard definitions, metric calculations, "
        "(8) Access Control Levels by role, (9) Integrations overview, "
        "(10) Non-compliance consequences."
    ),
    "Quarterly Sales Report": (
        "Create a Quarterly Sales Report template. Sections: Executive Summary "
        "(quarter highlights, vs target, vs prior quarter, vs prior year), "
        "Revenue Performance Dashboard — ARR, MRR, New Logo count, Expansion ARR, Churn ARR, NRR, "
        "Pipeline Analysis — stage breakdown table, coverage ratio, velocity metrics, "
        "Win/Loss Analysis (win rate by segment, top loss reasons), "
        "Rep Performance table — Rep | Quota | Attainment | Pipeline | Forecast, "
        "Key Deals section (top 5 won, top 5 at-risk), "
        "Product/Segment Mix, Forecast vs Actuals variance analysis, "
        "Next Quarter Priorities, and Risk & Opportunity Register."
    ),
    "Customer Feedback Report": (
        "Build a Customer Feedback Report. Include: Survey Methodology & Response Rate, "
        "NPS Score trend (current quarter vs 3 previous), CSAT and CES scores, "
        "Verbatim Themes Analysis — Top 5 positive themes (with representative quotes "
        "and frequency count), Top 5 negative themes with root causes, "
        "Segment Analysis (by customer tier, industry, geography, tenure), "
        "At-Risk Customer flags (Detractors list with owner assignments), "
        "Action Items table — Insight | Action | Owner | Due Date | Status, "
        "Closed-loop tracking table, and Executive Recommendations."
    ),

    # ── Engineering & Operations ──────────────────────────────────────────
    "Software Requirements Specification (SRS)": (
        "Write a complete SRS following IEEE 830 structure. Include: Introduction (purpose, scope, "
        "definitions, acronyms, overview), Overall Description (product perspective, "
        "product functions, user classes, constraints, assumptions), Specific Requirements — "
        "Functional Requirements (use case tables: ID | Name | Actor | Precondition | Main Flow | "
        "Alternate Flow | Postcondition), Non-Functional Requirements (performance targets, "
        "scalability, availability, security, usability benchmarks), System Interfaces, "
        "Data Requirements (entities and relationships described in text), Error Handling catalogue, "
        "and Requirements Traceability Matrix."
    ),
    "Technical Design Document (TDD)": (
        "Write a TDD covering: Problem Statement and context, Goals and Non-Goals, "
        "High-Level Architecture (components, data flow described textually), "
        "Detailed Design — each component/service with API contracts "
        "(endpoint, method, request/response schema), Data Model (entities, fields, "
        "types, relationships), Technology Choices with rationale and alternatives considered, "
        "Security Design (auth, authorisation, secrets management, input validation), "
        "Error Handling Strategy, Testing Strategy (unit, integration, E2E coverage targets), "
        "Deployment Plan, Rollout Strategy (feature flags, canary, percentages), "
        "Observability (metrics, logs, alerts defined), and Open Questions."
    ),
    "API Documentation": (
        "Write production-grade API Documentation. Sections: Overview (base URL, versioning, "
        "authentication — API key / OAuth2 / JWT with examples), Error Response catalogue "
        "(error code | HTTP status | meaning | resolution), Rate Limiting policy, "
        "For each endpoint — Method, Path, Description, Path/Query/Header Parameters table, "
        "Request Body schema with field descriptions and validation rules, "
        "Response schema with example JSON, Error responses specific to endpoint, "
        "and Code Examples in Python and JavaScript. Include a Quickstart section "
        "and a Changelog table."
    ),
    "Deployment Guide": (
        "Write a Deployment Guide. Prerequisites checklist (infrastructure, access, tools, env vars), "
        "Architecture overview (environments: dev, staging, production), "
        "Step-by-step deployment procedure (numbered, with exact commands and expected output "
        "after each command), Environment variable reference table — Var Name | Description | "
        "Required | Default, Database migration steps, Smoke test checklist, "
        "Rollback procedure (step-by-step), Health check endpoints and expected responses, "
        "Monitoring setup (dashboards to verify post-deploy), "
        "Common errors troubleshooting table — Error | Cause | Fix, "
        "and Deployment sign-off checklist."
    ),
    "Release Notes": (
        "Write structured Release Notes. Sections: Release header (version number, release date, "
        "release type — major/minor/patch), Executive Summary (one paragraph for non-technical "
        "stakeholders), New Features (feature name | description | benefit | how to enable), "
        "Improvements & Enhancements, Bug Fixes table (bug ID | title | severity | affected versions), "
        "Breaking Changes (highlighted prominently — what changes, migration steps, deadline), "
        "Deprecations with sunset timeline, Known Issues (ID | description | workaround | "
        "target fix version), Upgrade Instructions (step-by-step), "
        "and Documentation links."
    ),
    "System Architecture Document": (
        "Write a System Architecture Document. Include: Architecture Goals & Constraints "
        "(non-functional requirements driving design decisions), Architecture Principles, "
        "System Context diagram (described textually — actors, external systems, integrations), "
        "Container/Service Architecture (each service: responsibility, tech stack, communication "
        "protocol, port), Data Architecture (storage technologies per use case, "
        "data flow, retention policy), Security Architecture (network segmentation, "
        "encryption in transit/at rest, identity management), "
        "Infrastructure Architecture (cloud provider, regions, AZs, IaC tooling), "
        "Scalability & Resilience patterns used (circuit breaker, retry, bulkhead etc.), "
        "Monitoring & Observability stack, and Architecture Decision Records (ADRs) × 5."
    ),
    "Incident Report": (
        "Write a formal Incident Report. Structure: Incident summary (one paragraph), "
        "Severity classification and business impact (users affected, revenue impact, "
        "SLA breach status), Chronological Timeline (HH:MM:SS format — detection, "
        "triage, escalation, mitigation, resolution events), "
        "5-Why Root Cause Analysis (drill down 5 levels), "
        "Fishbone / Ishikawa analysis covering People / Process / Technology / Environment, "
        "Impact Assessment (quantified: users impacted, downtime minutes, "
        "data affected, financial impact), Immediate Actions Taken, "
        "Action Items table — ID | Action | Owner | Due Date | Success Criteria, "
        "Lessons Learned (by category), and Post-Incident Review meeting details."
    ),
    "Root Cause Analysis (RCA)": (
        "Write a rigorous RCA document. Include: Problem Statement (precise, quantified — "
        "what happened, when, where, how much impact), Timeline of events, "
        "5-Why Analysis chain (show each 'Why' level explicitly), "
        "Fishbone Diagram analysis — for each branch (People, Process, Technology, "
        "Environment, Materials, Measurement) list contributing causes, "
        "Root Cause Statement (concise, specific), "
        "SMART Corrective Actions table — Action | Root Cause Addressed | Owner | "
        "Due Date | Success Metric | Verification Method, "
        "Preventive Actions (systemic changes to prevent recurrence class), "
        "Effectiveness Validation Plan with review dates."
    ),
    "DevOps Runbook": (
        "Write a DevOps Runbook. Sections: Purpose and when to use this runbook, "
        "Prerequisites (access, tools, permissions checklist), "
        "Step-by-step procedures with exact commands, flags, and arguments, "
        "Expected output or screenshots description after each step, "
        "Verification steps (how to confirm success), "
        "Troubleshooting table — Symptom | Probable Cause | Diagnostic Command | Fix, "
        "Rollback procedure (numbered, with commands), "
        "Escalation path (who to call, in what order, with contact role titles), "
        "Time estimates per section, and a Post-task checklist."
    ),
    "Change Management Log": (
        "Create a Change Management Log template and policy. Include: "
        "Change Request Form template (fields: CR ID, Title, Requestor, Date, Change Type, "
        "Systems Affected, Description, Justification, Risk Assessment, "
        "Rollback Plan, Approval Status), "
        "Change Classification matrix (Standard/Normal/Emergency × impact/urgency), "
        "Approval Authority table by change type and risk level, "
        "Change Advisory Board (CAB) process and meeting cadence, "
        "Implementation checklist (pre/during/post), "
        "Risk Scoring matrix (Likelihood × Impact = Score → approval tier), "
        "Post-Implementation Review template, "
        "and a populated example log with 5 sample change records."
    ),

    # ── Product & Design ──────────────────────────────────────────────────
    "Product Requirements Document (PRD)": (
        "Write a complete PRD. Sections: Problem Statement (quantified with data), "
        "Goals & Success Metrics (OKR format: Objective + 3 Key Results with targets and baselines), "
        "Non-Goals (explicit scope exclusions), Background & Context, "
        "User Stories table — ID | As a [user type] | I want [action] | So that [outcome] | "
        "Acceptance Criteria | Priority (MoSCoW), "
        "Functional Requirements (numbered, testable), "
        "Non-Functional Requirements (performance, security, accessibility), "
        "UX Requirements & Wireframe Notes, Technical Constraints, "
        "Dependencies & Risks, Launch Plan (phases), and Open Questions log."
    ),
    "Product Roadmap": (
        "Write a narrative Product Roadmap document. Include: Product Vision (1-3 year), "
        "Strategic Themes (3-5 themes with rationale), "
        "Roadmap Table — Theme | Initiative | Problem Addressed | Outcome Target | "
        "Timeline (Now/Next/Later) | Status | Dependencies, "
        "OKRs per quarter (2 quarters in detail), "
        "Resource & Capacity Plan, "
        "Discovery Pipeline (items under research), "
        "What We Are NOT Building (deliberate exclusions), "
        "Stakeholder Communication Plan, "
        "Roadmap Change Process (how requests are evaluated and prioritised), "
        "and Metrics Dashboard definition."
    ),
    "Feature Specification Document": (
        "Write a Feature Specification Document. Sections: Feature Summary (one paragraph), "
        "Problem & Opportunity (user research evidence, quantified impact), "
        "Success Metrics (primary + secondary metrics with measurement method), "
        "User Personas impacted, "
        "Detailed User Stories with Acceptance Criteria "
        "(Gherkin format: Given/When/Then for each), "
        "UI/UX Specification (screen flows described, key interactions, "
        "error states, empty states, loading states), "
        "API Contract (endpoints affected), "
        "Data Model Changes, "
        "Edge Cases & Constraints, "
        "Out of Scope, "
        "Testing Requirements, "
        "Analytics & Instrumentation Plan, "
        "and Roll-out Plan (flags, segments, timeline)."
    ),
    "UX Research Report": (
        "Write a UX Research Report. Include: Research Objectives & Questions, "
        "Methodology (method chosen — usability test / interviews / survey / diary study — "
        "with rationale), Participant Criteria & Recruitment (screener questions), "
        "Research Protocol / Discussion Guide, "
        "Findings section — for each finding: Insight statement, "
        "Supporting evidence (quotes, task success rates, time-on-task), Severity rating, "
        "Recommendation, "
        "Affinity Map / Themes analysis, "
        "Jobs-to-be-Done statements × 5, "
        "Usability metrics table (task success rate, error rate, SUS score, time on task), "
        "Prioritised Recommendations table, and Next Steps."
    ),
    "Wireframe Documentation": (
        "Write Wireframe Documentation. For each screen / user flow include: "
        "Screen Name and URL/route, User Goal for this screen, "
        "Component inventory (list every UI element and its purpose), "
        "Interaction specifications (click actions, hover states, transitions, "
        "keyboard navigation), "
        "Content requirements (text, images, data fields with max lengths), "
        "Responsive behaviour notes (mobile / tablet / desktop breakpoints), "
        "Accessibility requirements (ARIA labels, contrast ratios, focus order), "
        "Error and empty states, "
        "Data dependencies (APIs called), "
        "and Design annotations."
    ),
    "Design System Guide": (
        "Write a Design System Guide. Sections: Foundations — Color palette (hex values, "
        "semantic names, usage rules, accessibility contrast ratios), Typography scale "
        "(font family, sizes, weights, line heights per level), Spacing scale (8pt grid system), "
        "Iconography guidelines, Grid & Layout system; "
        "Components — for each component (Button, Input, Card, Modal, Table, etc.): "
        "Variants, States (default/hover/focus/disabled/error), "
        "Props/API, Do's and Don'ts, Accessibility notes; "
        "Patterns section (forms, navigation, empty states, loading states, error states); "
        "Contribution Process, Versioning Policy, and Governance model."
    ),
    "User Persona Document": (
        "Write a User Persona Document. Create 4-5 distinct personas. "
        "For each persona include: Name, Photo description, Demographics, "
        "Job Title & Company Profile, "
        "Goals & Motivations (primary and secondary), "
        "Frustrations & Pain Points, "
        "A Day in Their Life narrative, "
        "Technology Adoption profile, "
        "Decision-Making Criteria, "
        "Key Quote (first-person voice), "
        "How they discover and evaluate solutions, "
        "Touchpoints in the product journey, "
        "and ICP / persona priority tier. "
        "Conclude with a Persona Comparison Matrix."
    ),
    "A/B Testing Report": (
        "Write an A/B Testing Report. Sections: Experiment Overview (hypothesis, test name, "
        "owner, dates, version), "
        "Hypothesis & Success Metric (primary metric + guardrail metrics), "
        "Test Design (control vs variant descriptions, traffic split %, "
        "target audience, sample size calculation and rationale, "
        "minimum detectable effect), "
        "Results — metrics table: Metric | Control | Variant | Lift % | "
        "P-value | Statistical Significance | Confidence Interval, "
        "Segment Analysis (results by user segment), "
        "Qualitative Observations, "
        "Conclusion & Decision (ship / kill / iterate with rationale), "
        "Next Experiment Recommendations, "
        "and Learnings Log."
    ),
    "Product Strategy Document": (
        "Write a Product Strategy Document. Include: Market Context & Opportunity sizing "
        "(TAM/SAM/SOM), Customer Segmentation & ICP, "
        "Competitive Landscape (feature matrix vs 3 competitors), "
        "Differentiation & Positioning Statement, "
        "Product Vision (3-year), Product Bets (strategic initiatives with rationale), "
        "Metrics Framework (North Star Metric, L1 driver metrics, L2 diagnostic metrics), "
        "Build vs Buy vs Partner decisions, "
        "Resource Requirements, "
        "Risks & Mitigations (min 5), "
        "Go-to-Market strategy summary, "
        "and Success Milestones with review cadence."
    ),
    "Competitive Analysis Report": (
        "Write a Competitive Analysis Report. Include: Market Overview & Landscape Map, "
        "Competitor Profiles × 4 (each: company overview, product positioning, pricing, "
        "target customer, strengths, weaknesses, recent moves), "
        "Feature Comparison Matrix (our product vs each competitor × 20+ features), "
        "Pricing Comparison table, "
        "Go-to-Market & Sales Motion comparison, "
        "Customer Sentiment Analysis (G2/Capterra/TrustPilot themes), "
        "Win/Loss Analysis (reasons we win/lose vs each competitor), "
        "Whitespace Opportunities, "
        "Strategic Recommendations (3-5 actionable recommendations), "
        "and Monitoring Plan (how to keep this document updated)."
    ),

    # ── Marketing & Content ───────────────────────────────────────────────
    "Marketing Strategy Plan": (
        "Write a comprehensive Marketing Strategy Plan. Include: Executive Summary, "
        "Market Analysis (TAM/SAM/SOM, SWOT), ICP & Buyer Persona alignment, "
        "Messaging Framework (value proposition per segment, proof points), "
        "Channel Strategy table — Channel | Goal | Tactic | Budget % | KPI | Owner, "
        "Content Strategy (content pillars, formats, cadence, SEO integration), "
        "Demand Generation funnel (MQL → SQL → SAL → Opp → Won metrics and targets), "
        "Brand & Creative guidelines reference, "
        "Campaign Calendar (quarterly themes and major launches), "
        "Budget Allocation breakdown, "
        "Marketing Tech Stack, "
        "Measurement Framework (weekly / monthly / quarterly review cadence), "
        "and Risks & Contingencies."
    ),
    "Content Calendar": (
        "Create a detailed Content Calendar. Include: Editorial Mission statement, "
        "Content Pillars (4-5 themes with rationale and % allocation), "
        "Monthly calendar table — Week | Content Title | Format (blog/video/social/email) | "
        "Channel | Topic Pillar | Target Persona | CTA | Owner | Status | Publish Date, "
        "SEO Keyword targets per month, "
        "Distribution & Amplification plan per content type, "
        "Content Production Workflow (idea → brief → draft → review → publish → distribute), "
        "Repurposing Strategy (how one piece feeds multiple formats), "
        "Performance Metrics per content type, "
        "Quarterly themes aligned to product launches and seasonal events, "
        "and a Content Audit template for existing assets."
    ),
    "Brand Guidelines": (
        "Write comprehensive Brand Guidelines. Sections: Brand Story & Positioning "
        "(mission, vision, values, origin narrative), "
        "Verbal Identity — Brand Voice (4 attributes with descriptions and do/don't examples), "
        "Tone variations by context, Writing Style Guide, "
        "Messaging hierarchy (tagline → value prop → elevator pitch → boilerplate), "
        "Visual Identity — Logo usage rules (clear space, minimum size, approved backgrounds, "
        "prohibited uses), Color System (primary, secondary, neutral palettes — hex, RGB, CMYK, "
        "Pantone values + usage proportions), Typography System, Photography & Imagery Style, "
        "Iconography, Illustration Style; "
        "Digital Guidelines (web, social media templates), "
        "Brand Application Examples, and Governance & Approval Process."
    ),
    "SEO Strategy Document": (
        "Write an SEO Strategy Document. Include: SEO Audit Summary (current state — "
        "technical health, domain authority, traffic trends), "
        "Keyword Strategy — keyword universe table: Keyword | Monthly Volume | "
        "Difficulty | Intent | Current Rank | Target Rank | Priority, "
        "Technical SEO Roadmap (site speed, Core Web Vitals, crawlability, schema markup), "
        "On-Page Optimization Standards (title tag, meta description, H1-H3 templates, "
        "internal linking rules, image optimisation), "
        "Content SEO Plan (pillar pages + cluster structure), "
        "Link Building Strategy (target domains, outreach tactics, anchor text diversity), "
        "Local SEO plan (if applicable), "
        "Measurement Framework (tools, KPIs, reporting cadence), "
        "and a 90-day Quick Win Action Plan."
    ),
    "Campaign Performance Report": (
        "Write a Campaign Performance Report. Sections: Campaign Overview "
        "(name, dates, objectives, budget), "
        "Executive Summary & Key Takeaways, "
        "Performance vs Goals table — KPI | Goal | Actual | Delta | Status, "
        "Channel Performance breakdown "
        "(Paid Search, Paid Social, Email, Content, Events — "
        "each with spend, impressions, clicks, CTR, CPL, MQLs generated), "
        "Funnel Metrics (MQL → SQL → Opp → Won conversion rates vs benchmark), "
        "Creative Performance Analysis (top and bottom performing assets), "
        "Audience & Targeting Analysis, "
        "Budget Utilisation (planned vs actual by channel), "
        "Key Learnings & Insights, "
        "and Recommendations for next campaign."
    ),
    "Social Media Strategy": (
        "Write a Social Media Strategy. Include: Objectives (SMART, platform-specific), "
        "Audience Analysis per platform, "
        "Platform Strategy — for each platform (LinkedIn, Twitter/X, Instagram, YouTube): "
        "Audience, Content Mix %, Posting Frequency, Content Formats, KPIs, Voice/Tone, "
        "Content Pillars & Themes mapping to platforms, "
        "Community Management Protocol (response times, escalation, tone guide), "
        "Influencer & Partnership Framework, "
        "Paid Social strategy (budget, targeting approach, creative guidelines), "
        "Social Listening & Monitoring setup, "
        "Crisis Communication Protocol, "
        "Measurement Dashboard (metrics, tools, review cadence), "
        "and a 90-day Content Launch Calendar."
    ),
    "Email Marketing Plan": (
        "Write an Email Marketing Plan. Include: Programme Architecture "
        "(lifecycle stages: acquisition, onboarding, nurture, retention, re-engagement), "
        "Audience Segmentation Strategy (criteria, segment names, sizes), "
        "Email Programme Table — Programme | Trigger | Audience | Goal | Frequency | "
        "Success Metric | Owned By, "
        "Welcome Series (5-email sequence with subject lines and content briefs), "
        "Nurture Sequence (content + CTAs per buyer stage), "
        "Technical Setup (ESP, domain authentication, deliverability standards — "
        "SPF/DKIM/DMARC), "
        "GDPR/CAN-SPAM compliance checklist, "
        "A/B Testing roadmap, "
        "Reporting Framework (opens, clicks, CTR, revenue attributed), "
        "and List Health Management procedures."
    ),
    "Press Release Template": (
        "Write a Press Release template. Include: "
        "FOR IMMEDIATE RELEASE header, "
        "Compelling headline (outcome-led, under 100 characters), "
        "Subheadline (one sentence expansion), "
        "Dateline format, "
        "Lead paragraph (who, what, when, where, why — inverted pyramid), "
        "Body paragraphs (supporting details, context, market implications), "
        "Two executive quotes (CEO + partner/customer — templates), "
        "Company boilerplate (standard 75-word paragraph), "
        "Media Contact block, "
        "### end marker, "
        "Notes to Editors section, "
        "and a separate guidance sheet on how to customise the template for "
        "product launches, funding announcements, and partnership announcements."
    ),
    "Market Research Report": (
        "Write a Market Research Report. Include: Executive Summary & Key Findings, "
        "Research Objectives & Methodology (primary + secondary research description), "
        "Market Definition & Sizing (TAM/SAM/SOM with sources and assumptions), "
        "Market Segmentation Analysis, "
        "Market Trends & Drivers (min 5 trends with evidence), "
        "Competitive Landscape Overview, "
        "Customer Insights (survey / interview findings summarised as themes), "
        "Barriers to Entry & Market Risks, "
        "Regulatory Environment summary, "
        "Strategic Opportunities & Whitespace, "
        "Go-to-Market Implications, "
        "and Appendix: Research Methodology Details, Survey Instrument."
    ),
    "Lead Generation Plan": (
        "Write a Lead Generation Plan. Include: Lead Generation Goals "
        "(MQL/SQL targets by quarter, CAC target, LTV/CAC ratio target), "
        "ICP & Persona Alignment (which personas to target per channel), "
        "Channel Mix Strategy table — Channel | Tactic | Monthly MQL Target | "
        "Est. Cost per MQL | Budget | Owner, "
        "Content & Offers Strategy (gated assets, webinars, free tools per funnel stage), "
        "Inbound Strategy (SEO, content, social), "
        "Outbound Strategy (outreach sequences, tooling, cadence), "
        "Paid Acquisition Strategy (platforms, budget, targeting), "
        "Lead Scoring Model (demographic + behavioural scoring criteria and thresholds), "
        "Lead Handoff Process (MQL → SDR → AE), "
        "Nurture Strategy, "
        "and Measurement Framework."
    ),

    # ── Finance & Operations ──────────────────────────────────────────────
    "Annual Budget Plan": (
        "Write an Annual Budget Plan. Include: CFO Executive Summary, "
        "Budget Philosophy & Assumptions (macro environment, company growth targets, "
        "key planning assumptions table with rationale), "
        "Revenue Budget (by product line, by geography, by customer segment — "
        "with prior year actuals, current year forecast, next year budget, YoY % change), "
        "Headcount Plan (by department, new hires by quarter, total personnel cost), "
        "OpEx Budget by category (COGS, S&M, R&D, G&A) with detailed line items, "
        "CapEx Budget, "
        "Cash Flow Projection (monthly for first half, quarterly for second half), "
        "Key Metrics & Ratios (Rule of 40, ARR growth, burn multiple), "
        "Budget Scenarios (base / upside / downside), "
        "Budget Governance & Change Process."
    ),
    "Financial Statement Report": (
        "Write a Financial Statement Report. Include: Executive Summary "
        "(period performance vs budget and prior period), "
        "Income Statement (revenue, COGS, gross profit, operating expenses by category, "
        "EBITDA, net income — with budget vs actual vs prior period columns), "
        "Balance Sheet Summary (assets, liabilities, equity — key line items), "
        "Cash Flow Statement (operating, investing, financing activities), "
        "Key Financial Ratios table (gross margin, operating margin, "
        "current ratio, quick ratio, burn rate, runway months), "
        "Revenue Recognition notes, "
        "Variance Analysis (top 5 variances with explanation), "
        "Risks & Contingencies, "
        "and Next Period Outlook."
    ),
    "Expense Policy": (
        "Write a comprehensive Expense Policy. Include: Policy Purpose & Scope, "
        "Pre-Approval Requirements by expense category and amount threshold, "
        "Eligible vs Ineligible Expenses table, "
        "Per-Category Limits table — Category | Limit per Transaction | "
        "Monthly Limit | Approval Required Above | Receipt Required, "
        "Travel Policy (flights: class by trip duration, hotels: max per night by city tier, "
        "ground transport, meals per diem by location), "
        "Entertainment Policy, "
        "Home Office & Remote Work Allowance, "
        "Submission Process & Deadlines (system used, submission frequency, receipt requirements), "
        "Reimbursement Timeline, "
        "Non-Compliance Consequences, "
        "and Manager Approval Responsibilities."
    ),
    "Invoice Template": (
        "Create a professional Invoice Template with a complete guide. Include: "
        "Invoice header (company logo placeholder, company legal name, address, tax ID, "
        "contact details), Client details block, "
        "Invoice metadata (invoice number format, invoice date, due date, payment terms), "
        "Line Items table — # | Description | Quantity | Unit Price | Amount, "
        "Subtotal, Tax/VAT line (rate and amount), Discount line, Total Due, "
        "Payment Instructions (bank details, accepted payment methods, "
        "reference to use), Late Payment terms, "
        "Terms & Conditions block, "
        "and a companion guide covering invoice numbering conventions, "
        "VAT/tax treatment rules, credit note process, and dispute process."
    ),
    "Procurement Policy": (
        "Write a Procurement Policy. Include: Purchasing Authority Matrix "
        "(amount thresholds × approval tiers with role titles), "
        "Procurement Process flowchart described in text "
        "(requisition → sourcing → evaluation → approval → PO → receipt → payment), "
        "Vendor Selection Criteria (mandatory vs scored criteria, RFP/RFQ process), "
        "Vendor Onboarding Requirements (due diligence checklist — legal, financial, "
        "security, insurance, ESG), "
        "Preferred Vendor Programme, "
        "Contract Requirements by spend category and amount, "
        "Purchase Order terms, "
        "Three-way Match process, "
        "Conflict of Interest Declaration requirements, "
        "Non-Compliance consequences, "
        "and Emergency Procurement Procedure."
    ),
    "Revenue Forecast Report": (
        "Write a Revenue Forecast Report. Include: Forecast Summary "
        "(current quarter, next quarter, full year — vs budget and vs prior year), "
        "Forecast Methodology (bottoms-up + top-down reconciliation approach), "
        "Pipeline-to-Revenue Bridge (pipeline stages, conversion rates, "
        "average deal size, velocity), "
        "Recurring Revenue Waterfall (ARR bridge: opening ARR + new + expansion "
        "- churn - contraction = closing ARR), "
        "Forecast by Segment / Geography / Product, "
        "Risks to Forecast (deals at risk, customer health signals), "
        "Upside Scenarios, "
        "Sensitivity Analysis (key assumptions + impact of ±10% change), "
        "and Forecast Accuracy Tracking (prior quarters' accuracy history)."
    ),
    "Cash Flow Statement": (
        "Write a Cash Flow Statement and analysis. Include: "
        "Statement of Cash Flows (12-month, showing monthly columns) covering "
        "Operating Activities (net income, non-cash adjustments, working capital changes), "
        "Investing Activities (CapEx, software capitalisation, acquisitions), "
        "Financing Activities (debt, equity, repayments); "
        "Cash Runway Calculation (current cash ÷ monthly net burn = months of runway), "
        "Burn Rate Analysis (gross burn vs net burn trend), "
        "Working Capital Analysis (DSO, DPO, inventory days), "
        "Cash Flow Forecast (next 6 months with high/base/low scenarios), "
        "Liquidity Risk Assessment, "
        "and Cash Management Recommendations."
    ),
    "Vendor Payment Policy": (
        "Write a Vendor Payment Policy. Include: Payment Terms Standards "
        "(default net-30, tiered by vendor category), "
        "Payment Methods and controls for each method "
        "(ACH, wire, credit card, cheque), "
        "Invoice Processing SLA (receipt to payment timeline by payment method), "
        "Three-Way Match requirement, "
        "Early Payment Discount capture programme, "
        "Late Payment consequences and escalation, "
        "Vendor Bank Account Change Verification Process "
        "(critical fraud-prevention controls), "
        "Payment Run Schedule, "
        "Approval Authority for payment releases by amount, "
        "Emergency Payment Process, "
        "and Audit Controls & Reconciliation Requirements."
    ),
    "Cost Analysis Report": (
        "Write a Cost Analysis Report. Include: Executive Summary & Key Findings, "
        "Cost Base Overview (total cost breakdown by category, YoY trend), "
        "Unit Economics Analysis "
        "(CAC, LTV, Gross Margin per product/segment, contribution margin), "
        "Cost Driver Analysis (identify top 10 cost drivers with quantification), "
        "Cost per Revenue Dollar trend analysis, "
        "Benchmarking vs industry peers, "
        "Inefficiency & Waste Identification "
        "(categories with above-benchmark cost ratios), "
        "Cost Reduction Opportunities table — Opportunity | Est. Annual Saving | "
        "Effort | Timeline | Owner | Risk, "
        "Cost Optimisation Roadmap, "
        "and Measurement Framework (how savings will be tracked)."
    ),
    "Financial Risk Assessment": (
        "Write a Financial Risk Assessment. Include: Risk Assessment Framework "
        "(quantitative + qualitative approach), "
        "Financial Risk Register — Risk ID | Category | Description | "
        "Likelihood (1-5) | Impact (1-5) | Risk Score | Current Controls | "
        "Residual Risk | Mitigation Action | Owner | Review Date; "
        "Risk Categories: Market Risk (FX, interest rate), Credit Risk "
        "(customer concentration, bad debt), Liquidity Risk, "
        "Operational Risk (fraud, system failures), Compliance/Regulatory Risk, "
        "Strategic Risk; "
        "Stress Test Scenarios (3 scenarios with financial modelling narrative), "
        "Risk Appetite Statement, "
        "and Risk Monitoring & Escalation Framework."
    ),

    # ── Partnership & Alliances ───────────────────────────────────────────
    "Partnership Agreement": (
        "Draft a comprehensive Partnership Agreement. Clauses: Parties and recitals, "
        "Definitions, Partnership Objectives & Scope, "
        "Roles & Responsibilities of each party (detailed obligations table), "
        "Revenue Sharing Model (formula, timing, reporting, audit rights), "
        "Exclusivity provisions (scope, geography, duration), "
        "Intellectual Property (each party's IP, jointly created IP), "
        "Co-Marketing obligations (budget, approvals, brand guidelines), "
        "Performance Obligations & KPIs (minimum commitments), "
        "Term & Termination (convenience, for cause, performance triggers), "
        "Confidentiality, Governing Law, Dispute Resolution, "
        "and Exhibits: Joint Business Plan template, Brand Usage Guidelines."
    ),
    "Memorandum of Understanding (MoU)": (
        "Write a professional MoU. Include: Background & Recitals, "
        "Purpose & Scope of Collaboration, "
        "Objectives of the MoU (bullet format, quantified where possible), "
        "Responsibilities of Each Party (clear obligations table), "
        "Resource Commitments (financial, personnel, technology), "
        "Joint Governance Structure (steering committee, meeting cadence), "
        "Timeline & Milestones, "
        "Key Performance Indicators, "
        "Confidentiality provisions, "
        "IP ownership statement, "
        "Non-Binding Nature clause (or binding clause if required), "
        "Duration and review process, "
        "Termination provisions, "
        "and Signatory blocks."
    ),
    "Channel Partner Agreement": (
        "Draft a Channel Partner Agreement. Include: Appointment clause "
        "(reseller, referral, or VAR — specify), Territory and Market Restrictions, "
        "Products/Services Authorised to sell, "
        "Pricing & Discount Structure table, "
        "Ordering Process & Forecasting requirements, "
        "Partner Obligations (certification, pipeline reporting, min revenue commitments), "
        "Company Obligations (training, co-marketing fund, deal registration, lead sharing), "
        "Deal Registration Process & Protection, "
        "Partner Programme Tier thresholds and benefits, "
        "Audit rights on books and records, "
        "Co-marketing fund policy, "
        "Termination and partner data return obligations."
    ),
    "Affiliate Program Agreement": (
        "Write an Affiliate Programme Agreement. Include: Programme overview and eligibility, "
        "Application & Approval Process, "
        "Affiliate Obligations (brand use, traffic quality, prohibited methods), "
        "Commission Structure table — Product/Tier | Commission % or Fixed | "
        "Attribution Window | Payment Threshold | Payment Frequency, "
        "Tracking & Attribution methodology, "
        "Reporting access and transparency, "
        "Cookie Policy, "
        "Prohibited Promotion Methods (PPC on branded terms, spam, coupon stacking), "
        "Marketing Material approval process, "
        "Fraud Detection & Clawback provisions, "
        "Tax compliance (W-9/W-8BEN), "
        "Termination, and Programme Changes process."
    ),
    "Strategic Alliance Proposal": (
        "Write a Strategic Alliance Proposal. Include: Executive Summary "
        "(opportunity, proposed alliance, expected mutual value), "
        "Strategic Rationale (why this partner, market timing, synergies), "
        "Market Opportunity Analysis (TAM, target segment, competitive gap), "
        "Proposed Alliance Structure (type, exclusivity, geography, scope), "
        "Value Exchange Analysis (what each party brings and gains), "
        "Joint Go-to-Market Plan (target accounts, motions, launch timeline), "
        "Financial Projections (pipeline potential, revenue split, investment required), "
        "Risk Assessment & Mitigation, "
        "Governance Model (steering committee, decision rights, escalation), "
        "Proposed Terms Summary, "
        "and Implementation Roadmap (90-day quick start)."
    ),
    "Partner Onboarding Guide": (
        "Write a Partner Onboarding Guide. Sections: Welcome & Programme Overview, "
        "Partner Portal access and navigation guide, "
        "Onboarding Phases table — Phase | Activities | Resources | Owner | Duration | "
        "Completion Criteria, "
        "Product & Solution Training Curriculum (modules, delivery method, certification), "
        "Sales Enablement Kit (battlecards, pitch decks, demo environment access), "
        "Marketing Co-launch checklist, "
        "Technical Integration Checklist (if applicable — APIs, sandboxes, test credentials), "
        "Legal & Compliance Requirements (signed agreements, certifications), "
        "Go-to-Market Readiness Checklist, "
        "Partner Success KPIs and review cadence, "
        "Support Model & Escalation Path."
    ),
    "Joint Marketing Plan": (
        "Write a Joint Marketing Plan. Include: Partnership Overview & Co-marketing Objective, "
        "Target Audience (joint ICP definition, segment size), "
        "Messaging Framework (joint value proposition, proof points), "
        "Campaign Overview table — Campaign | Channel | Owner | Budget Split | "
        "Timeline | KPI | Success Metric, "
        "Co-Branded Content Plan (assets, approvals process, brand guidelines reference), "
        "Digital Campaign (paid, social, email — each party's roles), "
        "Events & Webinar Plan, "
        "Lead Sharing & Attribution Model (how leads are tracked and owned), "
        "MDF (Market Development Fund) allocation and claim process, "
        "Budget Breakdown by party, "
        "Reporting Cadence & Joint Dashboard, "
        "and Legal/Compliance Review checklist."
    ),
    "Revenue Sharing Agreement": (
        "Draft a Revenue Sharing Agreement. Include: Revenue Definition "
        "(what qualifies, exclusions, refunds treatment), "
        "Revenue Sharing Formula table — Product/SKU | Partner % | Company % | "
        "Effective From | Notes, "
        "Revenue Reporting obligations (frequency, format, system access), "
        "Payment Schedule and method, "
        "Audit Rights (frequency, scope, dispute resolution timeline), "
        "Minimum Payment Threshold, "
        "Tax Withholding provisions, "
        "Currency and FX Conversion rules, "
        "Clawback provisions (for refunds, fraud, breach), "
        "Modification process (how revenue share terms can be changed), "
        "and Termination effect on revenue share obligations."
    ),
    "Partner Performance Report": (
        "Write a Partner Performance Report. Include: Executive Summary "
        "(period highlights, top and underperforming partners), "
        "Portfolio Dashboard — Partner | Tier | Revenue Achieved | "
        "Target | Attainment % | Deals Won | Pipeline | NPS, "
        "Tier Analysis (% of partners at each tier, trend), "
        "Top 5 Partners deep-dive (deals, revenue, co-marketing activity), "
        "At-Risk Partners (below performance threshold — remediation plan), "
        "Partner Enablement Metrics (certifications, training completion), "
        "Co-Marketing Campaign Results, "
        "Partner Satisfaction Survey Results, "
        "QBR Action Items Tracker, "
        "and Recommendations for programme improvements."
    ),
    "NDA for Partners": (
        "Write a partner-specific Mutual NDA. Include: Clear definition of Confidential Information "
        "(broad definition covering technical, commercial, roadmap, customer data), "
        "Carve-outs (4 standard: public domain, prior knowledge, independent development, "
        "compelled disclosure with process), "
        "Authorised Disclosure — need-to-know only, employees/contractors bound, "
        "Third-Party sub-disclosure prohibition, "
        "Security Requirements for protection of confidential information, "
        "Permitted Purpose restriction, "
        "Return/Destruction obligations with certification, "
        "Survival Period (minimum 3 years after agreement end), "
        "Injunctive Relief provision, "
        "No License/No Partnership inference clause, "
        "and bilateral signature blocks."
    ),

    # ── IT & Internal Systems ─────────────────────────────────────────────
    "IT Policy Manual": (
        "Write a comprehensive IT Policy Manual with 10+ policies. For each policy: "
        "Policy Number, Effective Date, Owner, Scope, Policy Statement, Procedures, "
        "Roles & Responsibilities, Compliance Requirements, Non-compliance Consequences. "
        "Policies: Acceptable Use, Access Control, Password Management, "
        "Data Classification & Handling, Endpoint Security, Mobile Device Management, "
        "Software License Management, Vulnerability Management, "
        "Change Management, and Incident Response (IT perspective). "
        "Include a Technology Standards Matrix "
        "(approved software list by category) and an IT Governance structure."
    ),
    "Access Control Policy": (
        "Write an Access Control Policy. Include: Access Control Principles "
        "(Least Privilege, Need-to-Know, Separation of Duties, Zero Trust), "
        "User Lifecycle Management Procedures "
        "(provisioning, modification, deprovisioning with SLAs for each), "
        "Role-Based Access Control (RBAC) model — role definitions and entitlement matrix, "
        "Privileged Access Management (PAM) requirements, "
        "Multi-Factor Authentication (MFA) requirements by system sensitivity tier, "
        "Access Review Process (quarterly review cadence, revocation SLA), "
        "Emergency Access Procedure, "
        "Third-Party / Vendor Access controls, "
        "Remote Access requirements, "
        "Monitoring & Logging requirements, "
        "and Non-Compliance consequences."
    ),
    "IT Asset Management Policy": (
        "Write an IT Asset Management Policy. Include: Asset Lifecycle phases "
        "(procurement → deployment → maintenance → decommission), "
        "Asset Classification categories (hardware, software, cloud, mobile), "
        "Asset Tagging & Inventory requirements (tool used, update frequency), "
        "Procurement Process (approved vendors, purchase request workflow), "
        "Asset Assignment & Acknowledgment (user agreement template), "
        "Software License Tracking (true-up process, compliance monitoring), "
        "Maintenance & Patching Schedule by asset class, "
        "Asset Loss/Theft Reporting Process, "
        "Secure Decommissioning & Data Destruction (by data classification), "
        "Cloud Asset Management (IaaS/SaaS inventory), "
        "and Audit & Compliance Review cadence."
    ),
    "Backup & Recovery Policy": (
        "Write a Backup & Recovery Policy. Include: Backup Scope "
        "(systems, databases, files — with explicit exclusions), "
        "Backup Classification — system tier | RTO | RPO | Backup Frequency | "
        "Retention Period | Backup Type (full/incremental/snapshot) | Storage Location, "
        "Backup Procedures (automated + manual, encryption requirements), "
        "Offsite & Air-gapped backup requirements, "
        "Backup Verification Testing (schedule, test method, success criteria), "
        "Recovery Procedures (step-by-step for each backup type), "
        "Recovery Time Objective (RTO) validation process, "
        "Roles & Responsibilities, "
        "Incident Escalation for backup failures, "
        "and Compliance & Audit requirements."
    ),
    "Network Architecture Document": (
        "Write a Network Architecture Document. Include: Network Design Principles, "
        "Network Topology overview (zones: internet-facing, DMZ, internal, management), "
        "IP Addressing scheme and VLAN segmentation table, "
        "Perimeter Security (firewall rules summary, IDS/IPS), "
        "Remote Access Architecture (VPN or ZTNA), "
        "Wireless Network Architecture, "
        "DNS & DHCP architecture, "
        "Bandwidth & Capacity planning, "
        "Network Monitoring & Alerting setup, "
        "Redundancy & Failover design, "
        "Security Controls per zone, "
        "Physical & Cloud network integration, "
        "Change Management for network changes, "
        "and Network Diagram description (textual representation of topology)."
    ),
    "IT Support SOP": (
        "Write an IT Support SOP. Include: Support Tier Model "
        "(L1/L2/L3 definitions, responsibilities, escalation criteria), "
        "Ticket Lifecycle (creation → triage → assignment → resolution → closure → feedback), "
        "SLA Targets by priority — P1/P2/P3/P4: Response Time, Update Frequency, "
        "Resolution Time, Escalation Path, "
        "Common Issue Resolution Guides (top 10 issues with step-by-step fix), "
        "Major Incident Process (declaration criteria, war room, comms cadence), "
        "Service Request Catalogue (most common requests with fulfilment SLA), "
        "Knowledge Base maintenance responsibilities, "
        "CSAT measurement process, "
        "and Continuous Improvement metrics."
    ),
    "Disaster Recovery Plan": (
        "Write a Disaster Recovery Plan (DRP). Include: DRP Objectives (RTO/RPO per system), "
        "Disaster Scenarios covered (data centre failure, cyberattack, natural disaster, "
        "key person dependency), "
        "DR Team roles and contact roster (by role title), "
        "Activation Criteria and Decision Authority, "
        "System Recovery Priorities (Tier 1/2/3 classification with business justification), "
        "Step-by-step Recovery Procedures per scenario, "
        "Communication Plan (internal, customer, vendor, regulator notifications), "
        "DR Infrastructure description (hot/warm/cold standby), "
        "Testing Schedule and Test Types (tabletop, simulation, full failover), "
        "Return-to-Normal Procedures, "
        "and DR Plan Maintenance & Review cycle."
    ),
    "Software License Tracking Log": (
        "Create a Software License Tracking Log and management guide. Include: "
        "Log Structure — Software Name | Vendor | License Type | Total Seats | "
        "Assigned Seats | Available Seats | Expiry Date | Annual Cost | "
        "Renewal Owner | Contract Location | Notes; "
        "License Classification (perpetual, subscription, concurrent, OEM, open source), "
        "Compliance Risk Rating per software, "
        "True-Up Process (audit frequency, comparison method, procurement trigger), "
        "Open Source Governance (approved licenses, prohibited licenses like GPL in commercial code), "
        "Renewal Calendar and 90-day advance review process, "
        "Cost Optimisation Review criteria (underutilised licences), "
        "and a populated sample log with 15+ realistic software entries."
    ),
    "Internal System Audit Report": (
        "Write an Internal System Audit Report. Include: Audit Scope & Objectives, "
        "Audit Methodology (frameworks: ISO 27001, CIS Controls, SOC2 criteria referenced), "
        "Systems Audited list, "
        "Findings Summary dashboard (total findings by severity: Critical/High/Medium/Low/Info), "
        "Detailed Findings table — Finding ID | System | Control Domain | "
        "Observation | Risk | Severity | Recommendation | Management Response | Due Date, "
        "Critical & High Findings — one page per finding "
        "(evidence, root cause, detailed remediation steps), "
        "Compliance Status per control domain, "
        "Positive Observations, "
        "Remediation Roadmap with owners and dates, "
        "and Auditor Sign-off."
    ),
    "Hardware Procurement Policy": (
        "Write a Hardware Procurement Policy. Include: "
        "Approved Hardware Standards — by role type (executive, developer, operations, finance) "
        "with approved models and spec minimums; "
        "Procurement Request Process (form fields, approval workflow by value); "
        "Approved Vendors and Supplier Qualification requirements; "
        "Budget Approval Matrix by hardware category and cost threshold; "
        "Procurement Lead Times by category; "
        "Asset Tag and Inventory Registration requirements on receipt; "
        "Personal vs Corporate device rules (BYOD policy reference); "
        "Refresh Cycle by hardware category (laptops: 3 years, servers: 4 years, etc.); "
        "Warranty and Support contract requirements; "
        "Decommission and disposal process; "
        "and Emergency Procurement procedure."
    ),

    # ── Platform & Infrastructure Operations ─────────────────────────────
    "Infrastructure Architecture Document": (
        "Write an Infrastructure Architecture Document. Include: Architecture Principles "
        "(cloud-native, IaC, immutable infrastructure, least privilege), "
        "Infrastructure Overview (cloud provider, regions, account/subscription structure), "
        "Network Architecture (VPCs, subnets, security groups, ingress/egress controls), "
        "Compute Architecture (EC2/VM types, container platform — EKS/GKE/AKS, serverless), "
        "Storage Architecture (object, block, file — use cases and encryption), "
        "Database Architecture (primary DB, read replicas, caching layer, backup strategy), "
        "Identity & Access (IAM roles, service accounts, secret management), "
        "Observability Stack (metrics, logs, traces — tools and retention), "
        "CI/CD Pipeline Architecture, "
        "Cost Management approach, "
        "and Infrastructure ADRs × 5."
    ),
    "Cloud Deployment Guide": (
        "Write a Cloud Deployment Guide. Include: Prerequisites "
        "(IAM roles/permissions needed, tools to install, env vars to set), "
        "Repository and branch strategy, "
        "Infrastructure as Code setup "
        "(Terraform / Pulumi / CloudFormation — initialise, plan, apply steps), "
        "Step-by-step deployment commands for each environment "
        "(dev, staging, production) with exact flags and expected output, "
        "Environment variable and secrets injection (Vault / AWS Secrets Manager / etc.), "
        "Database migration steps, "
        "Post-deployment smoke test checklist, "
        "Rollback procedure (step-by-step with commands), "
        "Monitoring verification steps, "
        "Common Errors troubleshooting table, "
        "and Deployment Sign-off Checklist."
    ),
    "Capacity Planning Report": (
        "Write a Capacity Planning Report. Include: Current Capacity Baseline "
        "(CPU, memory, storage, network — actual utilisation vs provisioned), "
        "Traffic & Growth Trend Analysis (historical data, seasonality patterns), "
        "Demand Forecast (12-month projections with methodology), "
        "Capacity Gap Analysis — Component | Current | 6-Month Need | "
        "12-Month Need | Gap | Action Required, "
        "Scaling Strategy per component (vertical, horizontal, auto-scaling rules), "
        "Infrastructure Spend Forecast, "
        "Cost Optimisation opportunities "
        "(rightsizing, reserved instances, spot instances), "
        "Risk Assessment (what happens if growth exceeds forecast), "
        "Action Plan with owners and dates, "
        "and Review cadence."
    ),
    "Infrastructure Monitoring Plan": (
        "Write an Infrastructure Monitoring Plan. Include: Monitoring Objectives "
        "(MTTD/MTTR targets), "
        "Monitoring Stack (tools: Prometheus/Grafana/Datadog/CloudWatch etc.), "
        "Metrics Catalogue — Component | Metric | Description | Warning Threshold | "
        "Critical Threshold | Alert Channel | Owner, "
        "Log Management (sources, aggregation, retention, search), "
        "Distributed Tracing strategy, "
        "Synthetic Monitoring (external probes, endpoints monitored, frequency), "
        "Alert Routing & Escalation (PagerDuty/OpsGenie configuration described), "
        "On-Call Schedule & Responsibilities, "
        "Dashboard Standards (what every service dashboard must include), "
        "SLI/SLO/SLA definitions, "
        "and Monitoring Review cadence."
    ),
    "Incident Response Plan": (
        "Write an Incident Response Plan (IRP). Include: Incident Classification Matrix "
        "(Sev1/Sev2/Sev3/Sev4 with criteria and examples), "
        "Incident Response Phases: Preparation, Detection & Analysis, "
        "Containment, Eradication, Recovery, Post-Incident Review; "
        "Incident Response Team (roles by title: Incident Commander, "
        "Technical Lead, Comms Lead, Executive Sponsor), "
        "Communication Templates (internal, customer, regulator — per severity), "
        "Runbook reference for each incident type, "
        "War Room Protocol, "
        "Evidence Preservation procedures, "
        "RCA requirement trigger criteria, "
        "Regulatory Notification obligations and timelines, "
        "and Post-Incident Review (PIR) template."
    ),
    "SLA for Infrastructure": (
        "Write an Infrastructure SLA. Include: Covered Services list "
        "(each service with brief description), "
        "Availability Commitments table — Service | Tier | Monthly Uptime % | "
        "Max Downtime/Month | Measurement Method | Exclusions, "
        "Performance SLAs (response times, throughput, latency targets per service tier), "
        "Priority Matrix for infrastructure incidents — "
        "P1/P2/P3/P4: Criteria | Initial Response | Update Frequency | "
        "Resolution Target | Escalation Path, "
        "Maintenance Windows (schedule, advance notice requirements, "
        "emergency maintenance process), "
        "Service Credit formula and cap, "
        "Reporting (metrics, frequency, format, recipients), "
        "Exclusions from SLA, "
        "and Review & Renegotiation process."
    ),
    "Configuration Management Document": (
        "Write a Configuration Management Document. Include: "
        "Configuration Management Objectives (consistency, auditability, drift prevention), "
        "Scope (systems, services, infrastructure covered), "
        "Configuration Item (CI) Classification and inventory approach, "
        "Baseline Configuration Standards — by system type "
        "(OS hardening, service defaults, security settings), "
        "Infrastructure as Code (IaC) standards and repository structure, "
        "Configuration Change Process (linked to Change Management Policy), "
        "Configuration Drift Detection (tooling, scan frequency, auto-remediation rules), "
        "Configuration Audit & Review schedule, "
        "Secret & Credential Management standards, "
        "Environment Parity requirements (dev = staging ≈ production constraints), "
        "and Non-compliance remediation SLA."
    ),
    "Uptime & Availability Report": (
        "Write an Uptime & Availability Report. Include: Executive Summary "
        "(overall uptime % vs SLA commitment), "
        "Service Availability Dashboard — Service | SLA Target | Actual Uptime % | "
        "Downtime Minutes | SLA Met? | Incidents Count, "
        "Incident Log (for the period) — Date | Incident ID | Service | Duration | "
        "Severity | Root Cause Category | Customer Impact, "
        "MTTR and MTTD trends, "
        "SLA Credit Obligations (if any), "
        "Reliability Engineering Improvements delivered in period, "
        "Planned Maintenance summary, "
        "Top Reliability Risks for next period, "
        "and Actions from previous period report."
    ),
    "Infrastructure Security Policy": (
        "Write an Infrastructure Security Policy. Include: Security Principles "
        "(Zero Trust, Least Privilege, Defence in Depth, Secure by Default), "
        "Network Security Controls (segmentation, firewall rules process, "
        "IDS/IPS, DDoS protection), "
        "Identity & Access Management (IAM standards, privileged access, MFA requirements), "
        "Endpoint & Server Hardening Standards "
        "(CIS Benchmark tier reference per OS), "
        "Patch Management (criticality-based SLA table), "
        "Container & Kubernetes Security Standards, "
        "Cloud Security Controls (per provider — shared responsibility model), "
        "Secret Management requirements, "
        "Vulnerability Scanning frequency and remediation SLA, "
        "Security Monitoring & SIEM requirements, "
        "and Security Review gates in CI/CD pipeline."
    ),
    "Scalability Planning Document": (
        "Write a Scalability Planning Document. Include: "
        "Scalability Goals (target scale: users, requests/sec, data volume in 12/24 months), "
        "Current Architecture Scalability Assessment "
        "(bottlenecks identified per component), "
        "Scalability Patterns Applied or Planned "
        "(horizontal scaling, caching, CDN, database sharding, async processing, etc.), "
        "Auto-Scaling Configuration (trigger metrics, min/max instances, "
        "scale-up and scale-down thresholds), "
        "Load Testing Plan (tools, scenarios, pass/fail criteria), "
        "Database Scalability Strategy (read replicas, connection pooling, query optimisation), "
        "Dependency & Third-Party API Scalability constraints, "
        "Cost Model at Scale (projected infrastructure cost at each traffic milestone), "
        "and Scalability Risks & Mitigations."
    ),

    # ── Data & Analytics ──────────────────────────────────────────────────
    "Data Governance Policy": (
        "Write a Data Governance Policy. Include: Data Governance Framework "
        "(principles, objectives, organisational model), "
        "Data Stewardship Model "
        "(Data Owner, Data Steward, Data Custodian — roles, responsibilities), "
        "Data Classification Framework — "
        "Class | Definition | Examples | Handling Requirements | Access Controls, "
        "Data Quality Standards (accuracy, completeness, consistency, timeliness — "
        "with measurable thresholds), "
        "Metadata Management requirements, "
        "Data Lifecycle Management (creation, storage, use, archiving, deletion), "
        "Data Access Request Process, "
        "Master Data Management standards, "
        "Data Incident Reporting, "
        "Regulatory Compliance integration (GDPR, CCPA), "
        "and Governance Review cadence."
    ),
    "Data Dictionary": (
        "Write a comprehensive Data Dictionary. Structure: Introduction & how to use it, "
        "Naming Conventions & Standards (tables, columns, abbreviations), "
        "Entity Overview diagram described in text, "
        "For each table/entity — "
        "Table Name | Description | Domain | Owner | Update Frequency | Retention Period, "
        "For each field — "
        "Field Name | Data Type | Length | Nullable | Default | Primary/Foreign Key | "
        "Description | Business Definition | Valid Values / Domain | "
        "Example Values | Source System | PII flag | Sensitivity class; "
        "Relationship Descriptions (foreign key relationships explained in business terms), "
        "Calculated Fields & Business Rules, "
        "Change Log, "
        "and a minimum of 8 fully documented entities relevant to a SaaS company "
        "(e.g. Account, Contact, Subscription, Event, Invoice, User, Session, Feature)."
    ),
    "Business Intelligence (BI) Report": (
        "Write a BI Report. Include: Executive Dashboard Summary "
        "(company-wide KPIs with period-over-period comparison), "
        "Revenue Analytics (MRR/ARR trend, new vs expansion vs churn breakdown, "
        "revenue by segment/geo/product), "
        "Customer Analytics (total customers, new logos, churn rate, "
        "NRR, LTV, customer health distribution), "
        "Product Usage Analytics (DAU/MAU/WAU, feature adoption rates, "
        "engagement funnel), "
        "Sales Pipeline Analytics (pipeline coverage, stage conversion rates, "
        "velocity), "
        "Marketing Analytics (leads, MQLs, CAC, campaign attribution), "
        "Operational Metrics (SLA adherence, support ticket volume, CSAT), "
        "Data Quality Score, "
        "and Recommended Actions from data insights."
    ),
    "KPI Dashboard Documentation": (
        "Write KPI Dashboard Documentation. For each KPI include: "
        "KPI Name, Business Question it answers, "
        "Formula / Calculation (exact, with example), "
        "Data Source (table, field, query logic), "
        "Owner (role responsible for metric), "
        "Reporting Frequency, "
        "Target & Baseline, "
        "Acceptable Range (green/amber/red thresholds), "
        "How to interpret movements, "
        "Known Caveats or Data Quality issues. "
        "Cover min 20 KPIs across: Revenue, Customer, Product, Marketing, Sales, Operations. "
        "Include a Dashboard Design Specification "
        "(layout, filters, drill-down capabilities) "
        "and an Access Control matrix."
    ),
    "Data Pipeline Documentation": (
        "Write Data Pipeline Documentation. For each pipeline include: "
        "Pipeline Name, Owner, Business Purpose, "
        "Source Systems (system name, connection method, data format, access credentials location), "
        "Transformations Applied (describe each transformation step clearly), "
        "Destination (system, table/schema, write mode), "
        "Schedule / Trigger (cron expression or event trigger), "
        "SLA (max acceptable latency / completion time), "
        "Data Volume (rows/day, GB/run), "
        "Dependency Map (upstream and downstream pipelines), "
        "Error Handling & Alerting (failure modes, retry logic, alert recipients), "
        "Data Quality Checks built in, "
        "Lineage diagram described in text, "
        "and Runbook for common failures."
    ),
    "Data Quality Report": (
        "Write a Data Quality Report. Include: Data Quality Framework Overview "
        "(dimensions: completeness, accuracy, consistency, timeliness, uniqueness, validity), "
        "Scoring Methodology (how each dimension is scored 0-100), "
        "Executive Summary — Overall DQ Score and trend, "
        "Domain-by-Domain Analysis — Domain | Completeness | Accuracy | "
        "Consistency | Timeliness | Uniqueness | Overall Score | Trend, "
        "Critical Issues table — Issue ID | Table | Field | Dimension | "
        "Record Count Affected | Business Impact | Root Cause | Remediation | Owner | Due Date, "
        "Data Debt backlog prioritisation, "
        "Improvements delivered in period, "
        "and Targets for next period."
    ),
    "Analytics Strategy Document": (
        "Write an Analytics Strategy Document. Include: Analytics Vision and Maturity "
        "Assessment (current vs target state), "
        "Strategic Objectives (how analytics supports company goals), "
        "Analytics Use Case Prioritisation Matrix "
        "(impact vs effort for top 15 use cases), "
        "Data Architecture Strategy (modern data stack: ingestion, storage, "
        "transformation, serving, BI layer — tool choices with rationale), "
        "Self-Service Analytics Programme, "
        "Data Literacy & Enablement Plan, "
        "AI/ML Roadmap (top 5 ML use cases with business case), "
        "Governance & Data Quality Programme, "
        "Team Structure & Capabilities roadmap, "
        "Investment Plan (build vs buy vs partner decisions), "
        "and Success Metrics for the analytics function."
    ),
    "Predictive Model Report": (
        "Write a Predictive Model Report. Include: Executive Summary "
        "(model purpose, key result, recommended action), "
        "Business Problem Definition (quantified), "
        "Data Sources & Feature Engineering "
        "(features used, transformations, data quality assessment), "
        "Modelling Approach (algorithms evaluated, selection rationale), "
        "Model Performance Metrics — Metric | Train | Validation | Test | Benchmark, "
        "Feature Importance Analysis (top 10 features with business interpretation), "
        "Bias & Fairness Assessment, "
        "Model Limitations & Assumptions, "
        "Deployment Architecture (serving, monitoring, retraining triggers), "
        "Business Impact Quantification (projected uplift or cost saving), "
        "and Model Governance & Review schedule."
    ),
    "Data Privacy Impact Assessment": (
        "Write a GDPR Article 35-compliant Data Privacy Impact Assessment (DPIA). Include: "
        "Processing Activity Description (what, why, how, who), "
        "Necessity & Proportionality Assessment "
        "(is the processing justified, minimised, limited?), "
        "Risk Assessment table — Risk | Likelihood | Severity | Overall Risk Level | "
        "Existing Controls | Residual Risk | Mitigation Measures, "
        "Data Subjects affected and potential harms, "
        "Data Flow Mapping (sources, processors, transfers), "
        "Third-Party Processor Assessment, "
        "International Transfer safeguards, "
        "Retention & Deletion mechanism, "
        "Consultation with Data Protection Officer, "
        "Outcome Decision (proceed / proceed with mitigations / do not proceed), "
        "and Review trigger events."
    ),
    "Reporting Standards Guide": (
        "Write a Reporting Standards Guide. Include: Reporting Philosophy "
        "(single source of truth, data democratisation principles), "
        "Report Classification (operational / analytical / executive / ad-hoc), "
        "Naming Conventions & Versioning for reports, "
        "Data Source Standards (approved sources per metric domain), "
        "Metric Definitions Catalogue (how every reported metric is calculated — "
        "at least 15 key metrics fully defined), "
        "Visualisation Standards "
        "(chart type selection guide, colour palette, accessibility requirements), "
        "Report Request & Approval Process, "
        "Self-Service vs Managed Reporting decision framework, "
        "Distribution & Access Control standards, "
        "Report Retirement Process, "
        "and Quality Assurance checklist for new reports."
    ),

    # ── QA & Testing ──────────────────────────────────────────────────────
    "Test Plan Document": (
        "Write a comprehensive Test Plan following IEEE 829. Include: "
        "Test Plan Identifier, Introduction (scope, objectives, constraints), "
        "Test Items (systems and features in scope), "
        "Features to be Tested vs NOT Tested, "
        "Test Approach (test types: unit, integration, system, regression, performance, "
        "security, accessibility — rationale for each), "
        "Entry and Exit Criteria, "
        "Test Environment Specifications, "
        "Test Data Strategy, "
        "Tools & Infrastructure, "
        "Roles & Responsibilities table, "
        "Test Schedule & Milestones table, "
        "Risk Assessment (min 5 testing risks with mitigations), "
        "Defect Management Process, "
        "Metrics & Reporting cadence, "
        "and Approval sign-off block."
    ),
    "Test Case Template": (
        "Create a Test Case Template and guide. Template fields: "
        "Test Case ID (format: TC-[MODULE]-[NNN]), Test Suite, Module, Feature, "
        "Title, Description, Preconditions, Test Data required, "
        "Step # | Action | Test Data | Expected Result | Actual Result | Pass/Fail, "
        "Post-conditions, Test Type, Priority (P1-P4), "
        "Automation Status (automated/manual/to-be-automated), "
        "Linked Requirement ID(s), Defect IDs (if failed), "
        "Last Executed Date, Executed By, Execution Time (minutes). "
        "Include: 10 fully populated example test cases "
        "for a SaaS user authentication flow, "
        "Test Case naming conventions guide, "
        "Traceability Matrix example, "
        "and Test Case Review Checklist."
    ),
    "Test Strategy Document": (
        "Write a Test Strategy Document. Include: Quality Philosophy & Objectives, "
        "Scope & Coverage Model (risk-based testing approach), "
        "Test Levels & Types — for each: purpose, scope, tools, entry/exit criteria, "
        "Test Automation Strategy (pyramid model — unit/integration/E2E ratios, "
        "framework choices, flaky test policy, CI integration), "
        "Performance Testing Strategy (load, stress, soak, spike — scenarios and tools), "
        "Security Testing Strategy (SAST, DAST, pen test schedule), "
        "Accessibility Testing Strategy (WCAG 2.1 AA compliance process), "
        "Test Environment Strategy (environment matrix, data refresh), "
        "Test Data Management Strategy, "
        "Defect Management & Severity Classification, "
        "QA Metrics Framework "
        "(defect escape rate, test coverage, automation coverage, cycle time), "
        "and Release Quality Gates."
    ),
    "Bug Report Template": (
        "Create a Bug Report Template and Bug Triage Guide. Template fields: "
        "Bug ID, Title (concise, actionable), Reporter, Date Found, "
        "Environment (OS, browser, app version, test env), "
        "Severity (Critical/High/Medium/Low with definitions), "
        "Priority (P1-P4 with definitions), "
        "Component / Module, "
        "Steps to Reproduce (numbered, exact), "
        "Expected Behaviour, Actual Behaviour, "
        "Screenshots / Logs attachment note, "
        "Regression (was this previously working?), "
        "Workaround (if known), "
        "Root Cause (completed by dev), "
        "Fix Description, Fix Version, Verified By, Verified Date. "
        "Include: Severity vs Priority matrix, "
        "10 example populated bug reports, "
        "Bug Triage Meeting process, "
        "and Defect SLA table."
    ),
    "QA Checklist": (
        "Create a comprehensive QA Checklist suite. Include: "
        "Pre-Release QA Checklist (functional, regression, integration, performance gates), "
        "Functional Testing Checklist (positive, negative, boundary conditions, "
        "error handling), "
        "UI/UX Checklist (visual consistency, responsive design, form validation, "
        "navigation, error messages), "
        "API Testing Checklist (authentication, CRUD operations, error codes, "
        "rate limiting, schema validation), "
        "Security Testing Checklist (OWASP Top 10 items), "
        "Performance Checklist (load time thresholds, stress test criteria), "
        "Accessibility Checklist (WCAG 2.1 AA key criteria), "
        "Data Validation Checklist, "
        "Release Readiness Checklist "
        "(sign-off required from: Dev Lead, QA Lead, Product Owner, Security), "
        "and Post-Deployment Smoke Test Checklist."
    ),
    "Automation Test Plan": (
        "Write an Automation Test Plan. Include: Automation Objectives "
        "(target automation coverage %, regression cycle time reduction target), "
        "Automation Scope (what to automate vs keep manual — criteria and decision matrix), "
        "Test Automation Pyramid design "
        "(unit %, integration %, E2E % allocation with rationale), "
        "Tooling Selection — for each tier: tool, language, framework, rationale, "
        "Test Data Management Strategy for automated tests, "
        "CI/CD Integration (when tests run, failure policies, parallel execution), "
        "Flaky Test Policy (definition, max allowed %, remediation SLA), "
        "Reporting & Dashboards, "
        "Maintenance Model (who owns tests, review cadence, deprecation process), "
        "Automation ROI Calculation, "
        "and Phased Implementation Roadmap (Q1/Q2/Q3/Q4 milestones)."
    ),
    "Regression Test Report": (
        "Write a Regression Test Report. Include: Report Header "
        "(build version, test environment, execution date, executed by), "
        "Executive Summary (pass rate, critical failures, go/no-go recommendation), "
        "Test Execution Summary table — Suite | Total Cases | Passed | Failed | "
        "Skipped | Execution Time | Pass Rate %, "
        "Failed Test Cases table — TC ID | Title | Severity | Error Description | "
        "Defect ID | New vs Regression | Owner | Status, "
        "New Defects Found (summary and severity distribution), "
        "Known Issues carried forward, "
        "Coverage Analysis (features covered vs scope), "
        "Environment & Data Issues encountered, "
        "Trend Analysis (pass rate over last 5 releases), "
        "and Release Recommendation with conditions."
    ),
    "UAT Document": (
        "Write a User Acceptance Testing (UAT) Document. Include: "
        "UAT Objectives & Success Criteria, "
        "Scope (features included / excluded), "
        "UAT Participants (roles: business owner, end users, UAT coordinator, IT), "
        "UAT Environment Setup Guide, "
        "Test Data Preparation instructions, "
        "UAT Schedule & Timeline table, "
        "UAT Test Scripts — for each scenario: "
        "Scenario ID | Business Process | Steps | Expected Outcome | "
        "Actual Outcome | Pass/Fail | Tester | Date | Comments; "
        "Defect Reporting Process during UAT, "
        "Defect Severity Classification for UAT, "
        "UAT Sign-off Criteria (exit criteria), "
        "UAT Sign-off Form template, "
        "and Post-UAT handoff checklist."
    ),
    "Test Coverage Report": (
        "Write a Test Coverage Report. Include: Coverage Summary Dashboard "
        "(overall coverage %, trend over last 5 sprints/releases), "
        "Coverage by Test Type table — Type | Lines/Branches/Functions Covered | "
        "Total | Coverage % | Target % | Gap, "
        "Coverage by Module/Component table, "
        "Requirements Traceability Matrix "
        "(Requirement ID | Requirement | Test Case IDs | Coverage Status), "
        "Risk-Based Coverage Analysis "
        "(high-risk areas: coverage % vs risk level assessment), "
        "Uncovered Areas Analysis (why not covered, risk accepted or backlog item), "
        "Automation vs Manual Coverage split, "
        "Coverage Trend Analysis, "
        "Improvement Actions table — Module | Gap | Action | Owner | Sprint Target, "
        "and Coverage Gate Definitions for release approval."
    ),
    "Performance Testing Report": (
        "Write a Performance Testing Report. Include: Test Objectives & SLAs targeted, "
        "Test Environment Specification, "
        "Test Scenarios — Scenario Name | User Load | Duration | Ramp-up | Think Time, "
        "Results Summary Dashboard — Scenario | Avg Response Time | "
        "95th Percentile | 99th Percentile | Throughput (req/s) | "
        "Error Rate % | Peak Concurrent Users, "
        "Performance Thresholds met/failed table, "
        "Resource Utilisation under load (CPU, memory, DB connections, network), "
        "Bottleneck Analysis (identified constraints with evidence), "
        "Comparison vs Previous Release, "
        "Recommendations (quick wins + architectural improvements), "
        "and Go/No-Go for performance criteria."
    ),

    # ── Security & Information Assurance ─────────────────────────────────
    "Information Security Policy": (
        "Write a comprehensive Information Security Policy aligned to ISO 27001. Include: "
        "Policy Statement from CISO/CEO, "
        "Scope & Applicability, "
        "Information Security Objectives (SMART, aligned to business goals), "
        "Security Governance Structure (CISO, Security Committee, roles), "
        "Risk Management approach (ISO 27005 reference), "
        "Security Control Domains "
        "(cover all 14 ISO 27001 domains: access control, cryptography, physical security, "
        "operations security, communications security, supplier relationships, "
        "incident management, BCM, compliance), "
        "Responsibilities matrix (Board, CISO, Managers, all staff), "
        "Acceptable Use statement, "
        "Non-Compliance Consequences, "
        "Security Awareness Training requirement, "
        "and Policy Review cycle."
    ),
    "Cybersecurity Risk Assessment": (
        "Write a Cybersecurity Risk Assessment following NIST RMF. Include: "
        "Assessment Scope & Objectives, "
        "Risk Assessment Methodology (NIST SP 800-30 approach), "
        "Asset Inventory (systems, data, processes assessed), "
        "Threat Landscape Analysis (top threats relevant to company profile), "
        "Vulnerability Assessment findings, "
        "Risk Register — Risk ID | Asset | Threat | Vulnerability | "
        "Likelihood | Impact | Risk Rating | Current Controls | Residual Risk | Treatment, "
        "Top 10 Risks deep-dive (one paragraph each with detailed treatment plan), "
        "Risk Heat Map description (5×5 matrix narrative), "
        "Prioritised Remediation Roadmap, "
        "and Risk Acceptance sign-off table."
    ),
    "Vulnerability Assessment Report": (
        "Write a Vulnerability Assessment Report. Include: Assessment Scope "
        "(IP ranges, systems, applications, timeframe), "
        "Methodology (tools used: Nessus/Qualys/OpenVAS etc., scan types), "
        "Executive Summary (finding counts by severity: Critical/High/Medium/Low/Info), "
        "Critical & High Findings — for each: CVE ID | Title | Affected Systems | "
        "CVSS Score | Description | Evidence | Business Risk | Remediation Steps | "
        "Remediation Priority | Due Date; "
        "Medium & Low Findings summary table, "
        "Attack Surface Analysis, "
        "Trend Analysis (vs previous assessment), "
        "Remediation Roadmap with milestones, "
        "and Re-assessment plan."
    ),
    "Penetration Testing Report": (
        "Write a Penetration Testing Report. Include: Executive Summary "
        "(risk posture, critical findings, strategic recommendations), "
        "Assessment Scope, Rules of Engagement, and Testing Timeline, "
        "Methodology (PTES/OWASP/NIST reference, phases: recon, scanning, "
        "exploitation, post-exploitation, reporting), "
        "Attack Narrative (story of highest-severity attack chain), "
        "Findings Catalogue — Finding ID | Title | Severity | CWE/CVE | "
        "Description | Evidence (sanitised) | Impact | Recommendation | References, "
        "Risk Score Summary, "
        "Remediation Roadmap, "
        "Verified Mitigations (from previous assessment), "
        "and Attestation / Tester credentials block."
    ),
    "Security Audit Report": (
        "Write a Security Audit Report. Include: Audit Scope, Objectives, "
        "and Framework (ISO 27001 / SOC2 / NIST CSF / CIS Controls), "
        "Audit Methodology & Evidence Collection approach, "
        "Executive Summary with Overall Maturity Rating, "
        "Control Domain Assessment — Domain | Controls Assessed | "
        "Compliant | Non-Compliant | Partial | Maturity Score, "
        "Detailed Findings — Finding ID | Control | Requirement | "
        "Observation | Gap | Risk | Severity | Recommendation | Management Response | Due Date, "
        "Positive Observations, "
        "Non-compliance Summary with regulatory implications, "
        "Remediation Roadmap, "
        "and Certification Readiness Assessment."
    ),
    "Data Classification Policy": (
        "Write a Data Classification Policy. Include: "
        "Classification Framework — for each tier "
        "(Public / Internal / Confidential / Restricted / Top Secret): "
        "Definition, Examples, Labelling Requirement, Access Controls, "
        "Encryption Requirements, Transmission Rules, Storage Requirements, "
        "Retention & Disposal Method, Breach Notification obligations; "
        "Classification Process (how to classify new data), "
        "Reclassification Process, "
        "Employee Responsibilities, "
        "Third-Party Handling Requirements, "
        "Data Inventory & Mapping requirement, "
        "Special Category Data handling (GDPR Art. 9), "
        "Declassification Process, "
        "and Non-Compliance Consequences."
    ),
    "Business Continuity Plan (BCP)": (
        "Write a Business Continuity Plan. Include: BCP Objectives & Policy, "
        "Business Impact Analysis (BIA) — Process | Criticality | RTO | RPO | "
        "Manual Workaround | Dependencies, "
        "Risk Scenarios covered "
        "(cyber attack, data centre loss, key person dependency, pandemic, "
        "supply chain failure), "
        "Crisis Management Team (roles by title, contact protocol, authority levels), "
        "Activation Criteria & Declaration Process, "
        "Recovery Strategies per critical process, "
        "Communication Plan "
        "(internal escalation, customer notification, media, regulator), "
        "IT Disaster Recovery summary reference, "
        "Alternate Work Arrangements, "
        "Testing Programme (test types, annual schedule, exercise scenarios), "
        "Return-to-Normal Criteria, "
        "and BCP Maintenance & Review cycle."
    ),
    "Security Awareness Training Material": (
        "Write Security Awareness Training Material. Include: "
        "Programme Overview & Objectives, "
        "Module 1: Security Fundamentals (threats landscape, social engineering, "
        "phishing recognition — 5 example phishing scenarios with red flags), "
        "Module 2: Password & Authentication Security "
        "(password policy, MFA, password manager guidance), "
        "Module 3: Data Handling & Classification "
        "(handling rules by class, share / not-share scenarios), "
        "Module 4: Safe Computing (device security, Wi-Fi risks, "
        "BYOD rules, clean desk policy), "
        "Module 5: Incident Reporting (how to report, what to report, "
        "reporting channel, no-blame culture), "
        "Module 6: Remote Working Security, "
        "Knowledge Check Questions (5 per module with answer key), "
        "Completion Tracking requirements, "
        "and Annual Refresher Programme outline."
    ),

    # ── Legacy / generic types (fallback) ─────────────────────────────────
    "SOP": (
        "Write numbered step-by-step procedures (min 5 sub-steps each). Include WHO, WHAT, "
        "HOW, WHEN for every step. Add decision points with IF/THEN logic. Include a "
        "Roles & Responsibilities table. Reference actual tools in each step."
    ),
    "Policy": (
        "Use mandatory language: must/shall/is prohibited. Define scope precisely. Include "
        "compliance checklist, violation consequences (tiered), exceptions process, and "
        "reference specific laws."
    ),
    "Proposal": (
        "Include Executive Summary, quantified problem, phased solution, ROI analysis, "
        "Risk Register (5+ risks), budget breakdown by category, success KPIs with "
        "baseline/target, implementation timeline table."
    ),
    "SOW": (
        "Include explicit IN-SCOPE and OUT-OF-SCOPE lists. Deliverables table with acceptance "
        "criteria. RACI matrix. Payment schedule tied to milestones. Change request process. "
        "List 8+ assumptions."
    ),
    "Incident Report": (
        "Chronological timeline with HH:MM timestamps. Quantify impact (users, revenue, "
        "SLA breach). 5-Why Root Cause Analysis (5 levels deep). Action items table with "
        "Owner/Due Date/Success Criteria. Lessons Learned by People/Process/Technology."
    ),
    "FAQ": (
        "Write 18-20 Q&A pairs organised by category. Each answer must be complete and "
        "self-contained. Include escalation path. Mix basic and advanced questions written "
        "from end-user perspective."
    ),
    "Runbook": (
        "Prerequisites checklist. Numbered steps with exact commands/UI paths. Expected "
        "output after EACH step. Troubleshooting table: Symptom|Cause|Fix. Rollback "
        "procedure. Time estimates per section."
    ),
    "Playbook": (
        "5+ distinct scenarios with dedicated plays. Each play: Trigger→Assessment→"
        "Actions→Escalation→Resolution. Success metrics per play. Common mistakes to avoid. "
        "Decision tree for complex scenarios."
    ),
    "RCA": (
        "Problem statement (precise, quantified). Full 5-Why chain. Fishbone analysis "
        "(People/Process/Technology/Environment). SMART action items table. Effectiveness "
        "validation plan."
    ),
    "SLA": (
        "Service definition (in-scope AND excluded). SLA Metrics table with exact numbers. "
        "Priority matrix P1-P4 with response AND resolution times. Credit formula. "
        "Escalation matrix with contact roles."
    ),
    "Change Management": (
        "Change Request form template. Risk scoring matrix (Likelihood×Impact). Approval "
        "authority table by change type. Rollback trigger criteria. Communication plan "
        "template. Post-implementation review checklist."
    ),
    "Handbook": (
        "Table of Contents. 10+ substantive chapters. Policy + procedure + guidance "
        "integrated per chapter. Checklists and quick-reference tables throughout. FAQ at "
        "end of major chapters. Version history."
    ),
}



# ============================================================
# PROMPT BUILDER  — chain-of-thought scaffolded prompt
# ============================================================
def build_prompt(industry, department, document_type, question_answers, sections, doc_specs=None, is_regeneration=False, original_content=""):
    dept = DEPT_CONTEXT.get(department, {
        "focus": f"{department} operations",
        "tone_note": "professional and clear",
        "compliance_note": "standard industry compliance",
    })

    # Resolve specific instructions and length
    doc_instr = DOC_TYPE_INSTRUCTIONS.get(
        document_type,
        "Write a comprehensive professional document with detailed, actionable content for every section.",
    )
    # length = LENGTH_GUIDE.get(document_type, "3,000–4,500 words")
    
    # Extract document specifications for page/content limits
    doc_specs = doc_specs or {}
    min_pages = doc_specs.get('min_pages', 1)
    max_pages = doc_specs.get('max_pages', 10)
    target_words = doc_specs.get('target_words', 2000)
    doc_format = doc_specs.get('format', 'Standard')
    
    # OVERRIDE instructions for 1-page documents - MINIMAL content only
    if min_pages == 1 and max_pages == 1:
        doc_instr = (
            "❌ ONE PAGE ONLY - EXACTLY 150-200 WORDS:\n"
            "- STOP after signature line\n"
            "- NO bullet points, NO lists, NO sections, NO tables\n"
            "- Plain paragraphs only (greeting, body 2-3 short paragraphs, closing)\n"
            "- ESSENTIAL details: name, job title, salary, start date, offer window, sign here\n"
            "- Count every single word. If you exceed 200 words, you FAIL.\n"
            "- If you include benefits, conditions, HR details, you FAIL.\n"
            "- If document spans 2 pages, you FAIL."
        )
    
    # Build length constraint string with MAXIMUM emphasis for 1-page docs
    if min_pages == 1 and max_pages == 1:
        length_constraint = (
            "🎯 CRITICAL CONSTRAINT: 1 PAGE ONLY\n"
            "- Word count: EXACTLY 150-200 words\n"
            "- Format: Professional business letter\n"
            "- Structure: Greeting → 2-3 short paragraphs → closing line\n"
            "- Content: Name, job title, salary, start date, acceptance deadline, signature\n"
            "- FORBIDDEN: Tables, lists, bullet points, sections, HR jargon, long paragraphs\n"
            "- MANDATORY: Count every word. If ≥201 words or ≥2 pages, response is REJECTED.\n"
            "- Do NOT add any commentary, notes, or metadata after the letter ends."
        )
    elif max_pages <= 3:
        length_constraint = (
            f"🚨 CRITICAL: Keep to {max_pages} pages max (~{target_words} words).\n"
            f"   • Each page ≈ {target_words//max_pages} words\n"
            f"   • Short, direct paragraphs only\n"
            f"   • Eliminate filler and verbose sections"
        )
    elif max_pages <= 10:
        length_constraint = f"Target: {max_pages} pages (~{target_words} words). Thorough but focused."
    else:
        # Long documents - push for comprehensive content
        length_constraint = f"🎯 COMPREHENSIVE DOCUMENT: {max_pages} pages (~{target_words:,} words). Include ALL details, sections, examples."

    # ── Extract named answers ──────────────────────────────────────────────
    company_name    = question_answers.get("company_name", "the company")
    company_size    = question_answers.get("company_size", "Medium (51-200)")
    primary_product = question_answers.get("primary_product", "SaaS platform")
    target_market   = question_answers.get("target_market", "B2B")
    specific_focus  = question_answers.get("specific_focus", "")
    extra_context   = question_answers.get("additional_context", "") or question_answers.get("additional_ctx", "")
    tone_pref       = question_answers.get("tone_preference", "Professional & Friendly")
    geo_locations   = question_answers.get("geographic_locations", "Global / Remote-first")

    tools = question_answers.get("tools_used", "")
    tools_str = (
        ", ".join(tools) if isinstance(tools, list)
        else str(tools or f"Standard {department} tools (JIRA, Confluence, Slack, Google Workspace)")
    )

    compliance = question_answers.get("compliance_requirements", "") or question_answers.get("compliance_req", "")
    compliance_str = (
        ", ".join(compliance) if isinstance(compliance, list)
        else str(compliance or dept["compliance_note"])
    )

    # Document metadata
    doc_title   = question_answers.get("document_title", f"{document_type} — {department}")
    author      = question_answers.get("author_name", "")
    approved_by = question_answers.get("approved_by", "")
    version     = question_answers.get("document_version", "1.0")
    eff_date    = question_answers.get("effective_date", "")

    # Dept-specific context (e.g. HR Head, Legal Entity)
    skip = {
        "company_name", "company_size", "primary_product", "target_market",
        "tools_used", "specific_focus", "compliance_requirements", "compliance_req",
        "geographic_locations", "tone_preference", "additional_context", "additional_ctx",
        "document_title", "author_name", "approved_by", "document_version", "effective_date",
    }
    extra_lines = "\n".join(
        f"  • {k.replace('q_', '').replace('_', ' ').title()}: "
        + (", ".join(v) if isinstance(v, list) else str(v))
        for k, v in question_answers.items()
        if k not in skip and v and v not in ("(select)", "")
    ) or "  • No additional inputs provided"

    # Sections list
    sections_str = (
        "\n".join(f"  {i+1}. {s}" for i, s in enumerate(sections))
        if sections
        else (
            "  (Use the standard sections appropriate for this document type as defined "
            "in the Document-Type Specific Requirements below)"
        )
    )
    
    # Build auto-sections context if available
    auto_sections_context = ""
    if doc_specs and doc_specs.get('auto_sections'):
        auto_sections = doc_specs.get('auto_sections', [])
        auto_sections_context = "\n\nDocument Structure Requirements:\n"
        for sec in auto_sections:
            sec_name = sec.get('section_name', 'Unknown')
            content_type = sec.get('content_type', 'mixed')
            auto_gen = sec.get('auto_generate', False)
            
            if content_type == 'static':
                auto_sections_context += f"  • {sec_name} (AUTO-GENERATE — use standard template/boilerplate)\n"
            elif content_type == 'dynamic':
                auto_sections_context += f"  • {sec_name} (USER-PROVIDED — use answers from questionnaire)\n"
            else:
                auto_sections_context += f"  • {sec_name} (MIXED — combine template + user answers)\n"

    # Special formatting instruction for 1-page documents
    formatting_instruction = ""
    if max_pages == 1:
        formatting_instruction = (
            "\n\n⚠️  FORMATTING OVERRIDE FOR 1-PAGE DOCUMENTS:\n"
            "DO NOT USE MARKDOWN FORMATTING. Output as PLAIN TEXT only.\n"
            "• NO ## headers (use ALL CAPS LABELS instead)\n"
            "• NO tables (use simple key: value format)\n"
            "• NO bullet points (use numbered 1. 2. 3. items only)\n"
            "• NO bold/italic formatting\n"
            "• Keep whitespace MINIMAL\n"
            "This keeps the document to exactly 1 page when printed."
        )

    # SPECIAL HANDLING: Compress prompt for long documents (35+ pages)
    if max_pages > 10:
        return f"""You are a senior enterprise documentation specialist.
Generate a COMPLETE {document_type} for {company_name}.

STRICT REQUIREMENT: Write MINIMUM {target_words:,} words. This is MANDATORY.
DO NOT STOP until you have written at least {target_words:,} words.
DO NOT summarize. Write FULL content for every single section.
DO NOT write "End of Part" or "To be continued".

COMPANY: {company_name} | {company_size} employees | {industry} industry
DEPARTMENT: {department}

DOCUMENT INSTRUCTIONS:
{doc_instr}

RULES:
- Use "{company_name}" everywhere — never "the company"
- No placeholders, no TBD, no [Insert X]
- Each section: minimum 200 words, detailed and specific
- Include tables, numbered lists, checklists
- Professional formal tone

COMPLIANCE: {compliance_str}
TOOLS: {tools_str}

YOU MUST WRITE {target_words:,} WORDS. START NOW AND DO NOT STOP:
"""
    
    # STANDARD PROMPT FOR ALL OTHER DOCUMENTS
    base_prompt = f"""⚠️  LENGTH REQUIREMENT: {length_constraint}

You are a principal-level enterprise documentation specialist with 20+ years of experience producing \
{document_type} documents for {industry} SaaS companies, with deep expertise in {department}.

Your documents are used directly by executives, legal teams, and operational teams — production-ready on first draft.

═══════════════════════════════════════════════════════
COMPANY PROFILE
═══════════════════════════════════════════════════════
Company Name   : {company_name}
Company Size   : {company_size}
Industry       : {industry}
Product        : {primary_product}
Target Market  : {target_market}

═══════════════════════════════════════════════════════
DOCUMENT METADATA
═══════════════════════════════════════════════════════
Document Title : {doc_title}
Document Type  : {document_type}
Department     : {department}
Version        : {version}

═══════════════════════════════════════════════════════
DOCUMENT-TYPE SPECIFIC REQUIREMENTS
═══════════════════════════════════════════════════════
{doc_instr}

═══════════════════════════════════════════════════════
NON-NEGOTIABLE QUALITY RULES
═══════════════════════════════════════════════════════
1. COMPANY NAME: Use "{company_name}" throughout. NEVER "the company" or [placeholder].
2. NO PLACEHOLDERS: NEVER "[Insert X]", "TBD", "[Date]", "[Name]", "XX%".
3. REAL NUMBERS: Actual figures — timeframes, percentages, thresholds, counts.
4. TOOL REFERENCES: Name actual tools ({tools_str}) — not "the system".
5. SCALE: All policies fit {company_size} in {industry}.
6. COMPLIANCE: Integrate {compliance_str} naturally.
7. FORMATTING: ## for sections, ### subsections, **bold** for terms, tables for data, numbered/bullet lists.
8. OPENING: Document header with title, type, department, version, date, author, approver.
9. CLOSING: Version History table.

{formatting_instruction}
"""
    
    # Add enhancement regeneration mode
    if is_regeneration and original_content:
        # Preserve original structure but enhance content
        enhancement_prompt = f"""
═══════════════════════════════════════════════════════
🚀 ENHANCEMENT MODE - PRESERVE & UPGRADE
═══════════════════════════════════════════════════════

⚡ PRESERVE ORIGINAL STRUCTURE - ENHANCE CONTENT WITHIN EACH SECTION

You will enhance the document below while KEEPING its structure completely intact.

ORIGINAL DOCUMENT TO ENHANCE:
────────────────────────────────────────────────────────
{original_content[:3000]}  # Truncate very long docs
────────────────────────────────────────────────────────

ENHANCEMENT STRATEGY — DO NOT CHANGE SECTION STRUCTURE:
✓ KEEP all section headings exactly as they are
✓ KEEP all section order exactly as they are
✓ KEEP all original content within sections
✓ ADD WITHIN each section: (append to existing, don't replace)

WHAT TO ADD TO EACH SECTION:
1. COMPLIANCE DEPTH: Add references to {compliance_str} where relevant
   - Example: "As per SOC2 Type II standards..." / "Per GDPR Article 32..."
   
2. SPECIFIC NUMBERS: Add concrete figures, percentages, thresholds
   - Example: "Within 24 hours" → "Within 24 hours per SLA (95% target)"
   - Example: "Approved staff" → "Approved staff (max 7 per department)"
   
3. STRONG LANGUAGE: Add professional authority and confidence
   - Replace: "may consider" → "must implement"
   - Replace: "guidelines" → "mandatory requirements"
   - Replace: "and more" → specific completions
   
4. PROFESSIONAL FORMATTING:
   - Use **bold** for key terms (once per section)
   - Add [Table] for data where appropriate
   - Use numbered lists (1. 2. 3.) for procedures
   - Keep section length 150-400 words each
   
5. COMPANY PERSONALIZATION: Add {company_name} reference where applicable

EXPECTED OUTCOME:
- Same structure, same flow, same headings
- Richer content with compliance + numbers + authority
- Professional, executive-ready enhancement
- Score improvement: +10-15 points

OUTPUT: Generate the COMPLETE enhanced document maintaining the original structure.
"""
        return base_prompt + enhancement_prompt + f"\n\nBEGIN THE ENHANCED {document_type.upper()} NOW:\n"
    elif is_regeneration:
        # Fallback: no original content, use quality boost
        regeneration_boost = f"""
═══════════════════════════════════════════════════════
🚀 QUALITY BOOST MODE
═══════════════════════════════════════════════════════

Generate a high-quality version with:
• 8-10 comprehensive sections
• 6+ compliance standard references ({compliance_str})
• 25+ specific numbers, dates, and metrics
• Professional formatting with tables, lists
• Zero weak language or placeholders

Target score: 90+/100 (A-grade)
"""
        return base_prompt + regeneration_boost + f"\n\nBEGIN THE IMPROVED {document_type.upper()} FOR {company_name.upper()} NOW:\n"
    
    return base_prompt + f"\n\nBEGIN THE COMPLETE {document_type.upper()} FOR {company_name.upper()} NOW:\n"


# ============================================================
# MAIN FUNCTION — uses openai SDK directly (no LangChain)
# ============================================================
def generate_document(industry, department, document_type, question_answers, is_regeneration=False, original_content=""):
    """
    Generate a professional enterprise document using Azure OpenAI.

    Args:
        industry        : e.g. "SaaS"
        department      : one of the 13 department strings
        document_type   : one of the 130 document-type strings
        question_answers: dict of answers from the questionnaire
        is_regeneration : bool, if True, adds quality improvement instructions
        original_content: str, the original document content (for enhancement mode)

    Returns:
        str: The generated document content (Markdown)
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"🚀 Starting document generation:")
    logger.info(f"  • Document Type: {document_type}")
    logger.info(f"  • Department: {department}")
    logger.info(f"  • Industry: {industry}")
    logger.info(f"  • Company: {question_answers.get('company_name', 'Not specified')}")
    if is_regeneration:
        logger.info(f"  • MODE: ⚡ REGENERATION (Quality Enhancement)")
    logger.info(f"{'='*70}")
    
    # Retrieve template sections from DB if available
    sections = []
    doc_specs = {}
    try:
        from services.template_repository import get_template_by_type
        from services.questionnaire_repository import get_questionnaire_by_type
        import json
        
        template = get_template_by_type(document_type, department)
        if template:
            sections = template.get("structure", {}).get("sections", [])
        
        # Extract document specs from questionnaire
        questionnaire = get_questionnaire_by_type(department, document_type)
        if questionnaire:
            questions = questionnaire.get("questions", [])
            # Find _document_specs entry
            for q in questions:
                if q.get('id') == '_document_specs':
                    doc_specs = q.get('document_specs', {})
                    break
    except Exception:
        pass

    # Log document specifications
    if doc_specs:
        logger.info(f"📋 Document Specs: pages={doc_specs.get('min_pages')}-{doc_specs.get('max_pages')}, words={doc_specs.get('target_words')}")
    else:
        logger.warning(f"⚠️  No document specs found for {document_type}")

    prompt = build_prompt(industry, department, document_type, question_answers, sections, doc_specs, is_regeneration, original_content)

    # ── Load Azure OpenAI credentials ─────────────────────────────────────
    endpoint    = os.getenv("AZURE_LLM_ENDPOINT", "").rstrip("/")
    api_key     = (
        os.getenv("AZURE_OPENAI_LLM_KEY")
        or os.getenv("AZURE_OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    api_version = os.getenv("AZURE_LLM_API_VERSION", "2025-01-01-preview")
    deployment  = (
        os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        or os.getenv("AZURE_LLM_DEPLOYMENT")
        or "gpt-4.1-mini"
    )

    if not endpoint or not api_key:
        raise ValueError(
            "Missing Azure credentials in .env\n"
            "Required: AZURE_LLM_ENDPOINT  and  AZURE_OPENAI_LLM_KEY"
        )

    # Calculate max_tokens dynamically based on page specifications
    max_page = doc_specs.get('max_pages', 3)
    target_words = doc_specs.get('target_words', 1000)
    
    # Conversion: 1 word ≈ 1.25-1.33 tokens, use 1.3
    estimated_tokens = int(target_words * 1.3)
    
    # Add buffer and cap based on page count - ULTRA AGGRESSIVE FOR REGENERATION
    if max_page == 1:
        # 1-page doc: 150-200 words = ~195-260 tokens, cap at 300 to be safe
        max_tokens = 350 if is_regeneration else 300  # MORE tokens for regeneration
        temperature = 0.01 if is_regeneration else 0.10  # ABSOLUTE MINIMUM for regeneration (near-deterministic)
        logger.info(f"1-page document: max_tokens={max_tokens}, temp={temperature} (regeneration={'ULTRA-STRICT' if is_regeneration else 'strict'} mode, A-GRADE BOOST)")
    elif max_page <= 3:
        # 2-3 page doc: cap at 2000-2500 tokens
        max_tokens = max(1800, min(estimated_tokens + 700, 2800)) if is_regeneration else max(1500, min(estimated_tokens + 300, 2500))
        temperature = 0.15 if is_regeneration else 0.45  # EXTREMELY focused for regeneration (A-grade mode)
        logger.info(f"Short doc ({max_page} pages): max_tokens={max_tokens}, temp={temperature} (regeneration={'A-GRADE FOCUS' if is_regeneration else 'normal'})")
    elif max_page <= 10:
        # 4-10 page doc: cap at 3500-4000 tokens
        max_tokens = max(3200, min(estimated_tokens + 1000, 4000)) if is_regeneration else max(2500, min(estimated_tokens + 500, 3500))
        temperature = 0.20 if is_regeneration else 0.55  # VERY focused for regeneration (quality priority)
        logger.info(f"Medium doc ({max_page} pages): max_tokens={max_tokens}, temp={temperature} (regeneration={'A-GRADE MODE' if is_regeneration else 'normal'})")
    else:
        # Long docs (11+ pages): MAXIMUM TOKENS AVAILABLE
        # Handbook (35-40 pages = 13,000-15,000 words = ~17,000-19,500 tokens needed)
        max_tokens = 18000 if is_regeneration else 16000  # Extra tokens for regeneration boost
        temperature = 0.25 if is_regeneration else 0.60  # MUCH lower temp for A-grade quality control
        logger.info(f"Long doc ({max_page} pages): max_tokens={max_tokens}, temp={temperature} (regeneration={'A-GRADE BOOST' if is_regeneration else 'normal'}, MAXIMUM ALLOWED)")
    
    # ── Call Azure OpenAI via openai SDK ───────────────────────────────────
    try:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )

        # Build system message with special handling for 1-page docs
        system_msg = (
            "You are a principal-level enterprise documentation specialist. "
            "You produce complete, professionally formatted, immediately usable documents. "
            "You never use placeholder text, TBD, or [brackets]. "
            "You always use the exact company name provided. "
            "Every number, date, threshold, and tool reference must be realistic and specific. "
            "You are a principal-level enterprise documentation specialist. "
            "You produce complete, professionally formatted, immediately usable documents. "
            "You never use placeholder text, TBD, or [brackets]. "
            "You always use the exact company name provided. "
            "For LONG documents (35+ pages), you MUST write the FULL document. "
            "NEVER stop early. NEVER summarize. Write EVERY section completely. "
            "STRICT LENGTH ENFORCEMENT: If the document specifies 1 page, DO NOT generate more than 1 page. "
            "If it specifies 35-40 pages, you MUST write ALL 35-40 pages without stopping. "
            "If it specifies N pages, respect that limit absolutely."
        )
        
        # Add regeneration improvement instructions
        if is_regeneration:
            system_msg += (
                "\n\n⚡ REGENERATION MODE - QUALITY ENHANCEMENT:\n"
                "This is a regenerated version of a document. Your goals:\n"
                "1. IMPROVE OVERALL QUALITY: More precise language, better structure, stronger compliance\n"
                "2. INCREASE CLARITY: Simpler explanations, better formatting, more actionable content\n"
                "3. ADD COMPLETENESS: Fill in details, remove vague statements, ensure professional tone\n"
                "4. ENHANCE PROFESSIONALISM: Use industry best practices, add specialized terminology correctly\n"
                "5. ENSURE ACCURACY: Verify compliance requirements, use proper standards (GDPR, SOC2, ISO, etc.)\n"
                "Generate fresh content that significantly improves upon the original while maintaining consistency."
            )
        
        # For 1-page documents, add explicit word count requirement
        if max_page == 1:
            system_msg += (
                "\n\n⛔ CRITICAL FOR 1-PAGE DOCUMENTS:\n"
                "You MUST write between 150-200 words EXACTLY.\n"
                "Count every word. More than 200 = FAILURE. Less than 150 = FAILURE.\n"
                "Write plain text letter format only. NO markdown, NO formatting."
            )

        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "system",
                    "content": system_msg,
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,  # dynamically set based on page specs
            max_tokens=max_tokens,    # dynamically calculated based on page specs
        )

        # Log successful generation
        content = response.choices[0].message.content
        word_count = len(content.split())
        logger.info(f"✅ Document generated: {word_count} words, {len(content)} chars")
        
        return content

    except ImportError:
        raise ImportError("openai package not installed. Run: pip install openai>=1.0.0")
    except Exception as e:
        logger.error(f"❌ Azure OpenAI API call failed: {str(e)}", exc_info=True)
        raise RuntimeError(
            f"Azure OpenAI call failed: {str(e)}\n"
            f"Endpoint  : {endpoint}\n"
            f"Deployment: {deployment}\n"
            f"API Version: {api_version}"
        ) from e


