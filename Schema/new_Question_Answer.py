"""
new_Question_Answer.py
Complete Static + Dynamic Question & Answer System
- Auto-fills missing sections
- Smart document length (1 page for simple docs, 35+ pages for complex)
- Professional, accurate output for all 12 departments
"""

import streamlit as st
from datetime import date, datetime


# ══════════════════════════════════════════════════════════════════════
# DOCUMENT LENGTH CONFIG
# Controls how long each document should be
# ══════════════════════════════════════════════════════════════════════

DOCUMENT_LENGTH = {
    # SHORT — 1 page (400-600 words)
    "Offer Letter":                          "short",
    "Exit Interview Form":                   "short",
    "Bug Report Template":                   "short",
    "Change Management Log":                 "short",
    "Invoice Template":                      "short",
    "Test Case Template":                    "short",
    "Performance Appraisal Form":            "short",
    "Onboarding Checklist":                  "short",
    "Press Release Template":                "short",
    "QA Checklist":                          "short",

    # MEDIUM — 4-8 pages (2000-4000 words)
    "Employment Contract":                   "medium",
    "Non-Disclosure Agreement (NDA)":        "medium",
    "NDA for Partners":                      "medium",
    "Service Level Agreement (SLA)":         "medium",
    "SLA for Infrastructure":                "medium",
    "Sales Contract":                        "medium",
    "Vendor Contract Template":              "medium",
    "Affiliate Program Agreement":           "medium",
    "Channel Partner Agreement":             "medium",
    "Revenue Sharing Agreement":             "medium",
    "Partnership Agreement":                 "medium",
    "Memorandum of Understanding (MoU)":     "medium",
    "Intellectual Property Agreement":       "medium",
    "Master Service Agreement (MSA)":        "medium",
    "Leave Policy Document":                 "medium",
    "Code of Conduct":                       "medium",
    "Training & Development Plan":           "medium",
    "Deployment Guide":                      "medium",
    "Release Notes":                         "medium",
    "DevOps Runbook":                        "medium",
    "Incident Report":                       "medium",
    "Root Cause Analysis (RCA)":             "medium",
    "API Documentation":                     "medium",
    "Quarterly Sales Report":                "medium",
    "Campaign Performance Report":           "medium",
    "Customer Feedback Report":              "medium",
    "Financial Statement Report":            "medium",
    "Cash Flow Statement":                   "medium",
    "Cost Analysis Report":                  "medium",
    "Revenue Forecast Report":               "medium",
    "Partner Performance Report":            "medium",
    "Regression Test Report":                "medium",
    "UAT Document":                          "medium",
    "Test Coverage Report":                  "medium",
    "Uptime & Availability Report":          "medium",
    "KPI Dashboard Documentation":           "medium",
    "Business Intelligence (BI) Report":     "medium",
    "Predictive Model Report":               "medium",
    "Data Quality Report":                   "medium",
    "Capacity Planning Report":              "medium",
    "Vulnerability Assessment Report":       "medium",
    "Security Audit Report":                 "medium",
    "Compliance Audit Report":               "medium",
    "Internal System Audit Report":          "medium",
    "User Persona Document":                 "medium",
    "A/B Testing Report":                    "medium",
    "Competitive Analysis Report":           "medium",
    "UX Research Report":                    "medium",
    "Market Research Report":                "medium",
    "Customer Case Study":                   "medium",
    "Pricing Strategy Document":             "medium",
    "Content Calendar":                      "medium",
    "Lead Generation Plan":                  "medium",
    "Email Marketing Plan":                  "medium",
    "Social Media Strategy":                 "medium",

    # LONG — 15-25 pages (8000-12000 words)
    "IT Policy Manual":                      "long",
    "HR Policy Manual":                      "long",
    "Employee Handbook":                     "long",
    "Information Security Policy":           "long",
    "Data Governance Policy":                "long",
    "Business Continuity Plan (BCP)":        "long",
    "Disaster Recovery Plan":                "long",
    "Cybersecurity Risk Assessment":         "long",
    "Risk Assessment Report":                "long",
    "Penetration Testing Report":            "long",
    "Software Requirements Specification (SRS)": "long",
    "Technical Design Document (TDD)":       "long",
    "System Architecture Document":          "long",
    "Infrastructure Architecture Document":  "long",
    "Product Requirements Document (PRD)":   "long",
    "Annual Budget Plan":                    "long",
    "Financial Risk Assessment":             "long",
    "Sales Playbook":                        "long",
    "Marketing Strategy Plan":               "long",
    "Brand Guidelines":                      "long",
    "SEO Strategy Document":                 "long",
    "Test Plan Document":                    "long",
    "Test Strategy Document":                "long",
    "Automation Test Plan":                  "long",
    "Performance Testing Report":            "long",
    "Data Privacy Impact Assessment":        "long",
    "Analytics Strategy Document":           "long",
    "Access Control Policy":                 "long",
    "Backup & Recovery Policy":              "long",
    "IT Asset Management Policy":            "long",
    "Hardware Procurement Policy":           "long",
    "Network Architecture Document":         "long",
    "IT Support SOP":                        "long",
    "Software License Tracking Log":         "long",
    "Procurement Policy":                    "long",
    "Expense Policy":                        "long",
    "Vendor Payment Policy":                 "long",
    "Data Classification Policy":            "long",
    "Security Awareness Training Material":  "long",
    "Scalability Planning Document":         "long",
    "Infrastructure Security Policy":        "long",
    "Configuration Management Document":     "long",
    "Product Strategy Document":             "long",
    "Product Roadmap":                       "long",
    "Feature Specification Document":        "long",
    "Design System Guide":                   "long",
    "Wireframe Documentation":               "long",
    "Data Dictionary":                       "long",
    "Data Pipeline Documentation":           "long",
    "Reporting Standards Guide":             "long",
    "CRM Usage Guidelines":                  "long",
    "Customer Onboarding Guide":             "long",
    "Partner Onboarding Guide":              "long",
    "Strategic Alliance Proposal":           "long",
    "Joint Marketing Plan":                  "long",
}

LENGTH_INSTRUCTIONS = {
    "short": (
        "DOCUMENT LENGTH: SHORT — exactly 1 page / 300-500 words MAXIMUM.\n"
        "- Output MUST NOT exceed 500 words total\n"
        "- Format as a clean professional business letter or form\n"
        "- NO long paragraphs, NO extra sections, NO headers (## or ###)\n"
        "- Write only the essential content — date, names, key details, signature\n"
        "- STOP immediately after the final signature/closing line\n"
        "- Do NOT add commentary, notes, or extra sections after content ends"
    ),
    "medium": (
        "DOCUMENT LENGTH: MEDIUM — 4-8 pages / 1500-4000 words.\n"
        "- Cover all required sections with clear, substantive content\n"
        "- Each section: 1-3 paragraphs or a structured table/list\n"
        "- Include specific details, examples, and relevant clauses\n"
        "- Total output: 1500-4000 words\n"
        "- Do NOT pad with unnecessary content to reach word count"
    ),
    "long": (
        "DOCUMENT LENGTH: LONG — 35-40 pages / 13,000-15,000 words.\n"
        "CRITICAL: Generate SECTION BY SECTION with FULL PROFESSIONAL DETAIL:\n"
        "STRUCTURE & ORGANIZATION:\n"
        "- 8 major parts with 70+ numbered sections\n"
        "- Include cover page, table of contents, appendices\n"
        "- Professional formatting with clear chapter breaks\n"
        "CONTENT REQUIREMENTS PER SECTION:\n"
        "- Each section: 200-500 words MINIMUM (detailed, NOT summaries)\n"
        "- MUST include: definition, policy rationale, procedures, responsibilities, examples\n"
        "- Use numbered steps, tables, checklists, matrices, flowcharts\n"
        "- Include case studies and real-world scenarios\n"
        "- Professional business terminology and formal tone\n"
        "- Cross-references to related sections\n"
        "MANDATORY COMPONENTS:\n"
        "- 8 MAJOR PARTS with detailed introduction for each\n"
        "- 70+ NUMBERED SECTIONS (each substantive)\n"
        "- TABLES: Salary scales, benefits matrices, holiday schedules, policy matrices\n"
        "- CHECKLISTS: Action items, verification checklists, onboarding/offboarding\n"
        "- FLOWCHARTS: Decision trees, escalation paths, complaint procedures\n"
        "- APPENDICES: FAQs (50+ questions), Glossary, Acknowledgment form, Revision history\n"
        "QUALITY STANDARDS:\n"
        "- ZERO placeholders (use real company data, not [COMPANY NAME] style)\n"
        "- Professional formatting and visual hierarchy\n"
        "- Comprehensive yet readable (not overwhelming)\n"
        "- Legally compliant language and best practices\n"
        "NEVER:\n"
        "- Skip any required section\n"
        "- Use abbreviated or summary content\n"
        "- Include incomplete policies or 'TBD' items\n"
        "- Create sections shorter than 200 words\n"
        "TOTAL OUTPUT:\n"
        "- 13,000-15,000 words across 35-40 pages\n"
        "- If reaching token limit, complete the current section then stop\n"
        "- Ensure all 8 parts are represented"
    ),
}

# Exact document specs from Question_Answer.json
# Used to pass precise page/word targets into the prompt
DOCUMENT_SPECS = {
    # SHORT — 1 page
    "Offer Letter":              {"min_pages": 1,  "max_pages": 1,  "target_words": 200},
    "Exit Interview Form":       {"min_pages": 2,  "max_pages": 4,  "target_words": 1000},
    "Bug Report Template":       {"min_pages": 1,  "max_pages": 2,  "target_words": 500},
    "Change Management Log":     {"min_pages": 1,  "max_pages": 2,  "target_words": 500},
    "Invoice Template":          {"min_pages": 1,  "max_pages": 1,  "target_words": 300},
    "Test Case Template":        {"min_pages": 1,  "max_pages": 2,  "target_words": 500},
    "Performance Appraisal Form":{"min_pages": 3,  "max_pages": 8,  "target_words": 2000},
    "Onboarding Checklist":      {"min_pages": 1,  "max_pages": 3,  "target_words": 800},
    "Press Release Template":    {"min_pages": 1,  "max_pages": 2,  "target_words": 600},
    "QA Checklist":              {"min_pages": 1,  "max_pages": 3,  "target_words": 800},
    # MEDIUM — 4-8 pages
    "Employment Contract":       {"min_pages": 2,  "max_pages": 5,  "target_words": 1500},
    "Non-Disclosure Agreement (NDA)": {"min_pages": 2, "max_pages": 5, "target_words": 1500},
    "Service Level Agreement (SLA)":  {"min_pages": 3, "max_pages": 8, "target_words": 2000},
    "Leave Policy Document":     {"min_pages": 5,  "max_pages": 12, "target_words": 2500},
    "Code of Conduct":           {"min_pages": 15, "max_pages": 25, "target_words": 6000},
    # LONG — 35-40 pages (COMPREHENSIVE)
    "Employee Handbook":         {"min_pages": 35, "max_pages": 40, "target_words": 14000},
    "HR Policy Manual":          {"min_pages": 20, "max_pages": 30, "target_words": 7500},
    "IT Policy Manual":          {"min_pages": 20, "max_pages": 35, "target_words": 10000},
    "Information Security Policy":{"min_pages": 20, "max_pages": 35, "target_words": 10000},
}


# ══════════════════════════════════════════════════════════════════════
# DOCUMENT SECTION TEMPLATES
# ══════════════════════════════════════════════════════════════════════

DOCUMENT_SECTIONS = {

    # ── HR & People Operations ──────────────────────────────────
    "Offer Letter": [
        "1. Greeting & Offer Statement",
        "2. Position, Department & Reporting Line",
        "3. Compensation & Benefits",
        "4. Start Date & Probation Period",
        "5. Acceptance Instructions",
    ],
    "Employment Contract": [
        "1. Parties & Definitions",
        "2. Position, Role & Duties",
        "3. Compensation, Bonuses & Benefits",
        "4. Working Hours, Location & Flexibility",
        "5. Leave Entitlements",
        "6. Probation Period",
        "7. Performance Standards",
        "8. Termination & Notice Period",
        "9. Confidentiality & Non-Disclosure",
        "10. Intellectual Property Assignment",
        "11. Non-Compete & Non-Solicitation",
        "12. Governing Law & Dispute Resolution",
        "13. Entire Agreement & Amendments",
    ],
    "Employee Handbook": [
        "1. Document Metadata",
        "2. Table of Contents",

        "3. Welcome Message from CEO",
        "4. Company Overview",
        "5. Company History",
        "6. Company Vision and Mission",
        "7. Core Values",
        "8. Organizational Culture",

        "9. Employment Philosophy",
        "10. Equal Employment Opportunity Policy",
        "11. Diversity, Equity and Inclusion",
        "12. Anti-Harassment and Anti-Discrimination Policy",
        "13. Workplace Respect Policy",

        "14. Employment Categories and Job Classification",
        "15. Recruitment and Onboarding Process",
        "16. Probation and Confirmation Policy",
        "17. Employee Personnel Records Policy",

        "18. Work Schedule and Working Hours",
        "19. Attendance and Punctuality Policy",
        "20. Remote Work and Hybrid Work Policy",
        "21. Flexible Work Arrangements",

        "22. Compensation Policy",
        "23. Payroll and Salary Payment",
        "24. Overtime and Work Hours Compliance",
        "25. Employee Benefits Overview",
        "26. Health Insurance and Wellness Benefits",
        "27. Employee Incentive and Bonus Policy",

        "28. Leave and Time-Off Policies",
        "29. Vacation Leave Policy",
        "30. Sick Leave Policy",
        "31. Public Holiday Policy",
        "32. Maternity and Paternity Leave",
        "33. Emergency Leave and Unpaid Leave",

        "34. Performance Management Framework",
        "35. Probation Performance Evaluation",
        "36. Annual Performance Appraisal Process",
        "37. Employee Promotion and Career Development",
        "38. Training and Professional Development",

        "39. Workplace Code of Conduct",
        "40. Ethical Business Practices",
        "41. Conflict of Interest Policy",
        "42. Employee Behavior and Professionalism",
        "43. Dress Code and Appearance Policy",

        "44. IT and Acceptable Use Policy",
        "45. Data Privacy and Information Security",
        "46. Cybersecurity and Password Policy",
        "47. Email and Communication Policy",
        "48. Social Media Usage Policy",

        "49. Health and Safety Policy",
        "50. Workplace Safety Procedures",
        "51. Emergency and Disaster Response",
        "52. Accident Reporting Procedure",

        "53. Workplace Security Policy",
        "54. Visitor Management and Access Control",
        "55. Company Property Usage Policy",

        "56. Employee Grievance Redressal Process",
        "57. Internal Complaint Mechanism",
        "58. Disciplinary Action Framework",

        "59. Compliance and Legal Obligations",
        "60. Confidentiality and Non-Disclosure",
        "61. Intellectual Property Policy",
        "62. Regulatory Compliance Policy",

        "63. Travel and Expense Reimbursement Policy",
        "64. Business Conduct with Clients and Vendors",

        "65. Employee Resignation Procedure",
        "66. Notice Period and Separation Policy",
        "67. Exit Interview Process",

        "68. Employee Acknowledgment of Handbook",
        "69. Handbook Update and Revision Policy",
        "70. Revision History",
    ],
    "HR Policy Manual": [
        "1. Introduction & Purpose",
        "2. Scope & Applicability",
        "3. Recruitment & Selection Policy",
        "4. Onboarding & Orientation",
        "5. Compensation & Benefits Policy",
        "6. Working Hours & Attendance",
        "7. Leave Management Policy",
        "8. Performance Management",
        "9. Learning & Development Policy",
        "10. Code of Conduct",
        "11. Anti-Harassment & Equal Opportunity",
        "12. Disciplinary Procedures",
        "13. Grievance Procedures",
        "14. Health & Safety",
        "15. Data Privacy & Confidentiality",
        "16. Exit & Offboarding Policy",
        "17. Policy Review & Updates",
    ],
    "Onboarding Checklist": [
        "1. Pre-Joining Tasks",
        "2. Day 1 — Arrival & Setup",
        "3. Week 1 — Orientation Activities",
        "4. System & Tool Access",
        "5. HR Documentation",
        "6. 30-Day Check-In",
    ],
    "Performance Appraisal Form": [
        "1. Employee & Review Details",
        "2. Goals & KPI Achievement",
        "3. Competency Ratings",
        "4. Manager Comments",
        "5. Employee Self-Assessment",
        "6. Development Plan",
        "7. Overall Rating & Recommendation",
    ],
    "Leave Policy Document": [
        "1. Purpose & Scope",
        "2. Types of Leave & Entitlements",
        "3. Leave Application Process",
        "4. Leave Approval Workflow",
        "5. Carry Forward & Encashment",
        "6. Leave Without Pay",
        "7. Public Holidays",
        "8. Special Circumstances",
        "9. Policy Review",
    ],
    "Code of Conduct": [
        "1. Purpose & Scope",
        "2. Core Values & Ethical Principles",
        "3. Professional Behavior Standards",
        "4. Conflict of Interest",
        "5. Anti-Harassment & Non-Discrimination",
        "6. Confidentiality & Data Privacy",
        "7. Social Media & External Communications",
        "8. Asset & Resource Usage",
        "9. Gifts & Anti-Bribery",
        "10. Reporting Violations & Whistleblower Protection",
        "11. Consequences of Misconduct",
        "12. Acknowledgement",
    ],
    "Exit Interview Form": [
        "1. Employee & Departure Details",
        "2. Primary Reason for Leaving",
        "3. Job Satisfaction Rating",
        "4. Management Feedback",
        "5. Improvement Suggestions",
        "6. Rehire Recommendation",
    ],
    "Training & Development Plan": [
        "1. Overview & Objectives",
        "2. Skills Gap Analysis",
        "3. Training Programs & Curriculum",
        "4. Delivery Methods & Schedule",
        "5. Budget & Resources",
        "6. Success Metrics & KPIs",
        "7. Roles & Responsibilities",
        "8. Review & Evaluation",
    ],

    # ── Legal & Compliance ───────────────────────────────────────
    "Non-Disclosure Agreement (NDA)": [
        "1. Parties",
        "2. Definition of Confidential Information",
        "3. Obligations of Receiving Party",
        "4. Permitted Disclosures",
        "5. Exclusions from Confidentiality",
        "6. Term & Duration",
        "7. Return or Destruction of Information",
        "8. Remedies for Breach",
        "9. Governing Law & Jurisdiction",
    ],
    "Master Service Agreement (MSA)": [
        "1. Parties & Definitions",
        "2. Scope of Services",
        "3. Term & Renewal",
        "4. Fees, Payment Terms & Invoicing",
        "5. Intellectual Property Rights",
        "6. Confidentiality",
        "7. Representations & Warranties",
        "8. Indemnification",
        "9. Limitation of Liability",
        "10. Termination",
        "11. Dispute Resolution",
        "12. Governing Law",
        "13. General Provisions",
    ],
    "Data Processing Agreement (DPA)": [
        "1. Parties & Definitions",
        "2. Scope & Purpose of Processing",
        "3. Roles: Controller vs Processor",
        "4. Controller Obligations",
        "5. Processor Obligations",
        "6. Sub-Processors",
        "7. Data Subject Rights",
        "8. Security Measures",
        "9. Data Breach Notification",
        "10. Data Retention & Deletion",
        "11. Audit Rights",
        "12. Governing Law",
    ],
    "Privacy Policy": [
        "1. Introduction & Scope",
        "2. Information We Collect",
        "3. How We Use Your Information",
        "4. Legal Basis for Processing",
        "5. Data Sharing & Third Parties",
        "6. International Data Transfers",
        "7. Data Retention Policy",
        "8. User Rights",
        "9. Cookies & Tracking Technologies",
        "10. Security Measures",
        "11. Children's Privacy",
        "12. Changes to This Policy",
        "13. Contact & DPO Information",
    ],
    "Terms of Service": [
        "1. Acceptance of Terms",
        "2. Description of Service",
        "3. User Accounts & Registration",
        "4. User Responsibilities",
        "5. Prohibited Activities",
        "6. Intellectual Property",
        "7. Disclaimers & Warranties",
        "8. Limitation of Liability",
        "9. Indemnification",
        "10. Termination",
        "11. Governing Law",
    ],
    "Compliance Audit Report": [
        "1. Executive Summary",
        "2. Audit Scope & Objectives",
        "3. Methodology",
        "4. Regulatory Framework",
        "5. Key Findings",
        "6. Non-Conformances",
        "7. Risk Rating",
        "8. Recommendations",
        "9. Management Response",
        "10. Conclusion & Next Steps",
    ],
    "Risk Assessment Report": [
        "1. Executive Summary",
        "2. Scope & Methodology",
        "3. Risk Identification",
        "4. Risk Assessment Matrix",
        "5. Impact Analysis",
        "6. Likelihood Analysis",
        "7. Risk Mitigation Strategies",
        "8. Residual Risk",
        "9. Monitoring & Review Plan",
    ],
    "Intellectual Property Agreement": [
        "1. Parties", "2. IP Definition & Ownership",
        "3. Assignment of Rights", "4. License Grant",
        "5. Restrictions", "6. Confidentiality",
        "7. Warranties", "8. Governing Law",
    ],
    "Vendor Contract Template": [
        "1. Parties & Scope", "2. Services Description",
        "3. Payment Schedule", "4. Deliverables & Milestones",
        "5. Confidentiality", "6. IP Ownership",
        "7. Termination", "8. Governing Law",
    ],
    "Regulatory Compliance Checklist": [
        "1. Regulation Overview", "2. Applicability Assessment",
        "3. Compliance Requirements", "4. Current Status",
        "5. Gaps Identified", "6. Remediation Actions",
        "7. Responsible Owners", "8. Review Schedule",
    ],

    # ── Engineering & Operations ─────────────────────────────────
    "Software Requirements Specification (SRS)": [
        "1. Introduction & Purpose",
        "2. Project Scope",
        "3. Stakeholders & User Classes",
        "4. Assumptions & Dependencies",
        "5. Functional Requirements",
        "6. Non-Functional Requirements",
        "7. External Interface Requirements",
        "8. System Constraints",
        "9. Data Requirements",
        "10. Security Requirements",
        "11. Performance Requirements",
        "12. Acceptance Criteria",
        "13. Appendix & Glossary",
    ],
    "Technical Design Document (TDD)": [
        "1. Overview & Objectives",
        "2. System Architecture",
        "3. Technology Stack",
        "4. Component Design",
        "5. Database & Data Models",
        "6. API Design & Contracts",
        "7. Data Flow & Sequence Diagrams",
        "8. Security Design",
        "9. Error Handling Strategy",
        "10. Performance Considerations",
        "11. Testing Strategy",
        "12. Deployment Considerations",
        "13. Open Questions & Risks",
    ],
    "API Documentation": [
        "1. Overview & Purpose",
        "2. Base URL & Versioning",
        "3. Authentication & Authorization",
        "4. Request/Response Format",
        "5. Rate Limiting & Throttling",
        "6. Error Codes & Handling",
        "7. Endpoints Reference",
        "8. Sample Requests & Responses",
        "9. SDKs & Code Examples",
        "10. Changelog",
    ],
    "Deployment Guide": [
        "1. Overview & Prerequisites",
        "2. Environment Configuration",
        "3. Deployment Steps",
        "4. Configuration Management",
        "5. Database Migrations",
        "6. Smoke Testing",
        "7. Rollback Procedure",
        "8. Monitoring Post-Deploy",
    ],
    "Release Notes": [
        "1. Release Summary",
        "2. New Features",
        "3. Improvements",
        "4. Bug Fixes",
        "5. Known Issues",
        "6. Upgrade Instructions",
        "7. Compatibility Notes",
    ],
    "System Architecture Document": [
        "1. Executive Summary",
        "2. Architecture Overview & Principles",
        "3. System Components",
        "4. Data Flow Diagrams",
        "5. Integration Points",
        "6. Security Architecture",
        "7. Scalability & Performance Design",
        "8. Availability & Redundancy",
        "9. Technology Stack",
        "10. Deployment Architecture",
        "11. Architecture Decision Records (ADRs)",
    ],
    "Incident Report": [
        "1. Incident Summary",
        "2. Severity Classification",
        "3. Timeline of Events",
        "4. Systems & Users Affected",
        "5. Root Cause Analysis",
        "6. Impact Assessment",
        "7. Resolution Steps",
        "8. Preventive Actions",
        "9. Lessons Learned",
        "10. Action Items & Owners",
    ],
    "Root Cause Analysis (RCA)": [
        "1. Problem Statement",
        "2. Incident Timeline",
        "3. Contributing Factors",
        "4. 5-Why Analysis",
        "5. Fishbone Diagram Summary",
        "6. Root Cause",
        "7. Corrective Actions",
        "8. Preventive Measures",
        "9. Action Items, Owners & Deadlines",
        "10. Verification of Fix",
    ],
    "DevOps Runbook": [
        "1. Purpose & Scope",
        "2. Prerequisites & Access",
        "3. System Overview",
        "4. Operational Procedures",
        "5. Monitoring & Alerting",
        "6. Escalation Contacts",
        "7. Rollback Procedures",
        "8. Known Issues & Workarounds",
    ],
    "Change Management Log": [
        "1. Change Summary", "2. Change Classification",
        "3. Impact Assessment", "4. Approval Workflow",
        "5. Implementation Plan", "6. Rollback Plan",
        "7. Post-Change Review",
    ],

    # ── IT & Internal Systems ────────────────────────────────────
    "IT Policy Manual": [
        "1. Introduction & Purpose",
        "2. Scope & Applicability",
        "3. Roles & Responsibilities",
        "4. Acceptable Use of IT Resources",
        "5. User Account & Password Management",
        "6. Data Protection & Confidentiality",
        "7. Access Control & Authentication",
        "8. Device & Endpoint Security",
        "9. Network Security",
        "10. Email & Internet Usage",
        "11. Software Installation & Licensing",
        "12. Cloud Services Usage",
        "13. Remote Working Security",
        "14. Incident Reporting & Response",
        "15. Physical Security",
        "16. Third-Party & Vendor Access",
        "17. Monitoring & Audit",
        "18. Non-Compliance & Enforcement",
        "19. Policy Review & Update Cycle",
        "20. Glossary",
    ],
    "Access Control Policy": [
        "1. Purpose & Scope",
        "2. Access Governance Principles",
        "3. User Access Classification Levels",
        "4. Role-Based Access Control (RBAC)",
        "5. Authentication Requirements & MFA",
        "6. Privileged Access Management (PAM)",
        "7. Access Request & Approval Process",
        "8. Onboarding Access Provisioning",
        "9. Offboarding & Access Revocation",
        "10. Periodic Access Reviews",
        "11. Remote Access Controls",
        "12. Third-Party & Vendor Access",
        "13. Violations & Enforcement",
        "14. Audit & Monitoring",
    ],
    "IT Asset Management Policy": [
        "1. Purpose & Scope",
        "2. Asset Classification",
        "3. Asset Registration & Inventory",
        "4. Asset Assignment & Usage Rules",
        "5. Maintenance & Support",
        "6. Asset Transfer",
        "7. Asset Disposal & Sanitization",
        "8. Software Assets & Licensing",
        "9. Roles & Responsibilities",
        "10. Audit & Compliance",
    ],
    "Backup & Recovery Policy": [
        "1. Purpose & Scope",
        "2. Backup Classification & Scope",
        "3. Backup Schedule & Frequency",
        "4. Backup Storage & Retention",
        "5. Encryption & Security",
        "6. Recovery Procedures",
        "7. RTO & RPO Targets",
        "8. Testing & Verification",
        "9. Roles & Responsibilities",
        "10. Exceptions & Escalation",
    ],
    "Network Architecture Document": [
        "1. Network Overview",
        "2. Network Topology",
        "3. Core Components",
        "4. IP Addressing & Subnetting",
        "5. Security Zones & Firewalls",
        "6. Remote Access & VPN",
        "7. Wireless Networks",
        "8. Network Monitoring",
        "9. Disaster Recovery Network Design",
    ],
    "IT Support SOP": [
        "1. Purpose & Scope",
        "2. Support Tier Definitions",
        "3. Incident Logging & Categorization",
        "4. Priority Classification Matrix",
        "5. Resolution Workflow",
        "6. Escalation Matrix",
        "7. SLA Targets by Priority",
        "8. Communication Standards",
        "9. Knowledge Base Usage",
        "10. Problem Management",
        "11. Reporting & Metrics",
    ],
    "Disaster Recovery Plan": [
        "1. Purpose & Scope",
        "2. Recovery Objectives (RTO & RPO)",
        "3. Disaster Scenario Classification",
        "4. DR Team & Contacts",
        "5. Communication Plan",
        "6. System Recovery Procedures",
        "7. Data Recovery Procedures",
        "8. Application Recovery Steps",
        "9. Vendor & Third-Party Contacts",
        "10. DR Testing Schedule",
        "11. Plan Maintenance",
        "12. Appendix: System Inventory",
    ],
    "Software License Tracking Log": [
        "1. Purpose & Scope", "2. License Inventory Table",
        "3. License Allocation", "4. Expiry Tracking",
        "5. Compliance Checks", "6. Renewal Procedure",
        "7. Audit Trail",
    ],
    "Internal System Audit Report": [
        "1. Executive Summary", "2. Audit Scope & Objectives",
        "3. Methodology", "4. Systems Reviewed",
        "5. Key Findings", "6. Risks Identified",
        "7. Recommendations", "8. Management Response",
    ],
    "Hardware Procurement Policy": [
        "1. Purpose & Scope",
        "2. Hardware Standards & Specifications",
        "3. Approved Vendor List",
        "4. Procurement Process",
        "5. Approval Thresholds & Workflow",
        "6. Asset Tagging & Registration",
        "7. Warranty & Support",
        "8. Disposal & Decommission",
        "9. Compliance & Audit",
    ],

    # ── Security & Information Assurance ─────────────────────────
    "Information Security Policy": [
        "1. Introduction & Purpose",
        "2. Scope & Applicability",
        "3. Information Security Objectives",
        "4. Roles & Responsibilities (RACI)",
        "5. Information Classification",
        "6. Access Control",
        "7. Data Protection & Encryption",
        "8. Network & Endpoint Security",
        "9. Secure Development (SDLC)",
        "10. Physical & Environmental Security",
        "11. Third-Party & Supplier Security",
        "12. Incident Management",
        "13. Business Continuity",
        "14. Employee Training & Awareness",
        "15. Compliance, Monitoring & Audit",
        "16. Policy Violations & Enforcement",
        "17. Policy Review Cycle",
        "18. Glossary",
    ],
    "Cybersecurity Risk Assessment": [
        "1. Executive Summary",
        "2. Scope & Methodology",
        "3. Threat Intelligence Overview",
        "4. Asset Inventory & Classification",
        "5. Threat Identification",
        "6. Vulnerability Assessment",
        "7. Risk Rating Matrix (Likelihood x Impact)",
        "8. Risk Register",
        "9. Business Impact Analysis",
        "10. Mitigation Recommendations",
        "11. Residual Risk & Risk Acceptance",
        "12. Risk Monitoring Plan",
        "13. Conclusion",
    ],
    "Penetration Testing Report": [
        "1. Executive Summary",
        "2. Scope & Rules of Engagement",
        "3. Methodology (OWASP / PTES)",
        "4. Testing Environment",
        "5. Findings Summary Dashboard",
        "6. Critical Findings",
        "7. High Findings",
        "8. Medium Findings",
        "9. Low / Informational Findings",
        "10. CVSS Scores & Risk Ratings",
        "11. Remediation Recommendations",
        "12. Re-test Plan",
        "13. Conclusion",
    ],
    "Incident Response Plan": [
        "1. Purpose & Scope",
        "2. Incident Classification",
        "3. Response Team & Contacts",
        "4. Preparation Phase",
        "5. Detection & Analysis",
        "6. Containment Procedures",
        "7. Eradication & Recovery",
        "8. Communication Plan",
        "9. Post-Incident Review",
        "10. Evidence Handling & Chain of Custody",
        "11. Legal & Regulatory Notification",
    ],
    "Vulnerability Assessment Report": [
        "1. Executive Summary", "2. Assessment Scope & Tools",
        "3. Methodology", "4. Findings by Severity",
        "5. Detailed Vulnerability List", "6. Risk Analysis",
        "7. Remediation Recommendations", "8. Conclusion",
    ],
    "Security Audit Report": [
        "1. Executive Summary", "2. Audit Scope",
        "3. Controls Evaluated", "4. Key Findings",
        "5. Compliance Gaps", "6. Recommendations",
        "7. Management Response",
    ],
    "Data Classification Policy": [
        "1. Purpose & Scope",
        "2. Classification Levels & Definitions",
        "3. Classification Criteria",
        "4. Data Handling Rules per Level",
        "5. Labeling & Marking Requirements",
        "6. Storage & Transmission Rules",
        "7. Access Controls",
        "8. Data Disposal",
        "9. Employee Responsibilities",
        "10. Compliance & Audit",
    ],
    "Business Continuity Plan (BCP)": [
        "1. Purpose & Scope",
        "2. Business Impact Analysis (BIA)",
        "3. Critical Business Functions & Dependencies",
        "4. Recovery Time & Point Objectives",
        "5. Recovery Strategies",
        "6. Crisis Management Team",
        "7. Crisis Communication Plan",
        "8. IT Recovery (link to DRP)",
        "9. Alternate Site & Work-From-Home Procedures",
        "10. Supplier & Third-Party Continuity",
        "11. Testing & Exercise Schedule",
        "12. Plan Maintenance & Review",
        "13. Appendix: Contact Directory",
    ],
    "Security Awareness Training Material": [
        "1. Introduction & Objectives",
        "2. Why Security Awareness Matters",
        "3. Phishing & Social Engineering",
        "4. Password Security & MFA",
        "5. Safe Internet & Email Usage",
        "6. Data Handling & Privacy",
        "7. Device & Physical Security",
        "8. Remote Working Security",
        "9. Incident Reporting",
        "10. Acceptable Use Recap",
        "11. Assessment & Quiz",
    ],

    # ── Finance & Operations ─────────────────────────────────────
    "Annual Budget Plan": [
        "1. Executive Summary",
        "2. Budget Objectives & Strategy",
        "3. Economic & Business Assumptions",
        "4. Revenue Projections",
        "5. Operating Expense Budget",
        "6. Capital Expenditure Plan",
        "7. Department-wise Allocations",
        "8. Headcount & Compensation Plan",
        "9. Cash Flow Projection",
        "10. Budget vs Actuals Framework",
        "11. Variance Tracking Process",
        "12. Risk & Contingency",
        "13. Approval Summary",
    ],
    "Financial Statement Report": [
        "1. Executive Summary", "2. Income Statement",
        "3. Balance Sheet Summary", "4. Cash Flow Summary",
        "5. Revenue Analysis", "6. Expense Analysis",
        "7. Key Financial Ratios", "8. YoY Comparison",
    ],
    "Expense Policy": [
        "1. Purpose & Scope",
        "2. Expense Categories & Limits",
        "3. Pre-Approval Requirements",
        "4. Expense Submission Process",
        "5. Receipts & Documentation",
        "6. Reimbursement Process",
        "7. Corporate Card Usage",
        "8. Travel Expenses",
        "9. Prohibited Expenses",
        "10. Audit & Compliance",
    ],
    "Financial Risk Assessment": [
        "1. Executive Summary",
        "2. Risk Assessment Methodology",
        "3. Financial Risk Categories",
        "4. Risk Identification & Register",
        "5. Probability & Impact Matrix",
        "6. Risk Mitigation Strategies",
        "7. Contingency Plans",
        "8. Risk Monitoring Framework",
        "9. Conclusion & Recommendations",
    ],
    "Revenue Forecast Report": [
        "1. Executive Summary", "2. Forecast Methodology",
        "3. Revenue Assumptions", "4. Projected Revenue by Quarter",
        "5. Segment Analysis", "6. Risk Factors",
        "7. Scenario Analysis (Base/Bull/Bear)", "8. Recommendations",
    ],
    "Cash Flow Statement": [
        "1. Overview", "2. Operating Activities",
        "3. Investing Activities", "4. Financing Activities",
        "5. Net Cash Position", "6. Liquidity Analysis",
        "7. Forecast & Outlook",
    ],
    "Procurement Policy": [
        "1. Purpose & Scope",
        "2. Procurement Principles",
        "3. Vendor Selection & Evaluation",
        "4. Approval Thresholds",
        "5. Purchase Order Process",
        "6. Contract Management",
        "7. Supplier Relationship Management",
        "8. Compliance & Audit",
    ],
    "Vendor Payment Policy": [
        "1. Purpose & Scope", "2. Payment Terms",
        "3. Approved Payment Methods", "4. Invoice Validation",
        "5. Payment Schedule", "6. Dispute Resolution",
        "7. Compliance & Audit",
    ],
    "Invoice Template": [
        "1. Invoice Header & Number",
        "2. Billing Parties",
        "3. Line Items & Descriptions",
        "4. Tax & Total",
        "5. Payment Terms & Instructions",
        "6. Notes",
    ],
    "Cost Analysis Report": [
        "1. Executive Summary", "2. Analysis Scope",
        "3. Cost Categories", "4. Cost Drivers",
        "5. Variance Analysis", "6. Benchmarking",
        "7. Cost Reduction Opportunities", "8. Recommendations",
    ],

    # ── Sales & Customer Facing ──────────────────────────────────
    "Sales Proposal Template": [
        "1. Cover Page & Executive Summary",
        "2. Understanding of Client Needs",
        "3. Proposed Solution",
        "4. Scope of Work & Deliverables",
        "5. Implementation Timeline",
        "6. Pricing & Investment",
        "7. Why Us — Differentiators",
        "8. Case Studies & References",
        "9. Terms & Conditions",
        "10. Next Steps & Call to Action",
    ],
    "Sales Playbook": [
        "1. Introduction & Purpose",
        "2. Company & Product Overview",
        "3. Ideal Customer Profile (ICP)",
        "4. Sales Process Stages",
        "5. Lead Qualification (BANT/MEDDIC)",
        "6. Discovery Questions Bank",
        "7. Objection Handling Guide",
        "8. Competitive Battlecards",
        "9. Demo & Presentation Guide",
        "10. Pricing & Negotiation Guidelines",
        "11. Closing Strategies",
        "12. CRM Usage & Hygiene Rules",
        "13. Success Metrics & KPIs",
    ],
    "Customer Onboarding Guide": [
        "1. Welcome & Overview",
        "2. Onboarding Timeline & Milestones",
        "3. Account Setup Steps",
        "4. Key Contacts & Support Channels",
        "5. Training Resources",
        "6. Integration Guide",
        "7. Success Metrics",
        "8. FAQs & Troubleshooting",
    ],
    "Service Level Agreement (SLA)": [
        "1. Parties & Purpose",
        "2. Service Scope",
        "3. Uptime & Availability Commitments",
        "4. Incident Priority Definitions",
        "5. Response & Resolution Times",
        "6. Support Hours & Channels",
        "7. Maintenance Windows",
        "8. Reporting & Review",
        "9. SLA Penalties & Service Credits",
        "10. Exclusions",
        "11. Governing Law",
    ],
    "Quarterly Sales Report": [
        "1. Executive Summary",
        "2. Revenue vs Target",
        "3. Pipeline Analysis",
        "4. New Customer Acquisition",
        "5. Retention & Churn",
        "6. Sales by Region/Segment",
        "7. Product/Service Performance",
        "8. Challenges & Learnings",
        "9. Next Quarter Forecast",
    ],
    "Customer Case Study": [
        "1. Customer Overview",
        "2. Challenge & Problem",
        "3. Solution Implemented",
        "4. Results & Outcomes",
        "5. Customer Quote",
        "6. Key Takeaways",
    ],
    "CRM Usage Guidelines": [
        "1. Purpose & Scope",
        "2. CRM System Overview",
        "3. Data Entry Standards",
        "4. Lead & Opportunity Management",
        "5. Activity Logging Rules",
        "6. Reporting & Dashboards",
        "7. Access Roles & Permissions",
        "8. Data Quality & Hygiene",
        "9. Integration Rules",
        "10. Compliance & Data Privacy",
    ],
    "Pricing Strategy Document": [
        "1. Executive Summary",
        "2. Pricing Objectives",
        "3. Market & Competitor Analysis",
        "4. Pricing Model",
        "5. Pricing Tiers & Packages",
        "6. Discounting Policy",
        "7. Cost Structure & Margins",
        "8. Review & Adjustment Process",
    ],
    "Customer Feedback Report": [
        "1. Executive Summary", "2. Feedback Sources & Methodology",
        "3. Overall Satisfaction Score", "4. Key Themes",
        "5. Positive Feedback", "6. Areas for Improvement",
        "7. Action Plan",
    ],

    # ── Product & Design ─────────────────────────────────────────
    "Product Requirements Document (PRD)": [
        "1. Overview & Problem Statement",
        "2. Goals & Success Metrics",
        "3. User Personas & Target Audience",
        "4. User Stories & Use Cases",
        "5. Functional Requirements",
        "6. Non-Functional Requirements",
        "7. Out of Scope",
        "8. Wireframes & Design References",
        "9. Technical Dependencies",
        "10. Risks & Assumptions",
        "11. Timeline & Milestones",
        "12. Open Questions",
    ],
    "Product Roadmap": [
        "1. Vision & Strategic Themes",
        "2. Roadmap Summary",
        "3. Prioritization Framework",
        "4. Now (Current Quarter)",
        "5. Next (Next Quarter)",
        "6. Later (6-12 Months)",
        "7. Dependencies & Risks",
        "8. Success Metrics",
    ],
    "Feature Specification Document": [
        "1. Feature Overview",
        "2. Business Justification",
        "3. User Stories",
        "4. Functional Specifications",
        "5. Technical Dependencies",
        "6. UI/UX Requirements",
        "7. Acceptance Criteria",
        "8. Edge Cases & Exclusions",
        "9. Testing Requirements",
    ],
    "UX Research Report": [
        "1. Research Objectives",
        "2. Methodology & Participants",
        "3. Research Timeline",
        "4. Key Findings",
        "5. Usability Issues",
        "6. Affinity Map / Themes",
        "7. User Quotes & Observations",
        "8. Recommendations",
        "9. Next Steps",
    ],
    "Competitive Analysis Report": [
        "1. Executive Summary", "2. Market Overview",
        "3. Competitor Profiles", "4. Feature Comparison Matrix",
        "5. Pricing Comparison", "6. SWOT Analysis",
        "7. Strategic Recommendations",
    ],
    "User Persona Document": [
        "1. Persona Overview",
        "2. Demographics & Background",
        "3. Goals & Motivations",
        "4. Pain Points & Frustrations",
        "5. Behaviors & Habits",
        "6. Technology Usage",
        "7. Quotes & Key Insights",
        "8. Design Implications",
    ],
    "Product Strategy Document": [
        "1. Vision & Mission",
        "2. Market Opportunity",
        "3. Target Segments",
        "4. Strategic Goals",
        "5. Product Positioning",
        "6. Competitive Differentiation",
        "7. Go-to-Market Strategy",
        "8. Resource Plan",
        "9. OKRs & Success Metrics",
    ],
    "A/B Testing Report": [
        "1. Experiment Overview",
        "2. Hypothesis",
        "3. Test Setup & Variants",
        "4. Metrics & Success Criteria",
        "5. Results",
        "6. Statistical Significance",
        "7. Conclusions & Recommendations",
    ],
    "Design System Guide": [
        "1. Introduction & Principles",
        "2. Color System",
        "3. Typography",
        "4. Spacing & Grid",
        "5. Iconography",
        "6. Component Library",
        "7. Motion & Animation",
        "8. Accessibility Standards",
        "9. Usage Guidelines & Do's/Don'ts",
        "10. Contribution & Governance",
    ],
    "Wireframe Documentation": [
        "1. Overview & Purpose",
        "2. Design Tool & File Links",
        "3. Information Architecture",
        "4. Screen Inventory",
        "5. Navigation Flow",
        "6. Key Interactions",
        "7. Component Notes",
        "8. Handoff Checklist",
    ],

    # ── Marketing & Content ──────────────────────────────────────
    "Marketing Strategy Plan": [
        "1. Executive Summary",
        "2. Market Analysis & Landscape",
        "3. Target Audience & Segments",
        "4. Marketing Objectives & KPIs",
        "5. Brand Positioning",
        "6. Channel Strategy",
        "7. Content Strategy",
        "8. Paid Media Plan",
        "9. Campaign Calendar",
        "10. Budget Allocation",
        "11. Technology & Martech Stack",
        "12. Measurement & Reporting",
        "13. Risks & Mitigations",
    ],
    "Brand Guidelines": [
        "1. Brand Story & Mission",
        "2. Brand Values",
        "3. Brand Voice & Tone",
        "4. Logo Usage Rules",
        "5. Color Palette",
        "6. Typography System",
        "7. Imagery & Photography",
        "8. Iconography",
        "9. Social Media Guidelines",
        "10. Email & Document Templates",
        "11. Do's & Don'ts",
    ],
    "SEO Strategy Document": [
        "1. SEO Objectives & KPIs",
        "2. Keyword Research Strategy",
        "3. On-Page Optimization",
        "4. Technical SEO",
        "5. Content Strategy",
        "6. Link Building",
        "7. Local SEO",
        "8. Competitor Analysis",
        "9. Tools & Reporting",
        "10. Roadmap & Priorities",
    ],
    "Content Calendar": [
        "1. Overview & Goals",
        "2. Content Themes & Pillars",
        "3. Channel-wise Schedule",
        "4. Content Types & Formats",
        "5. Posting Frequency",
        "6. Responsibility Matrix",
        "7. Review & Approval Workflow",
    ],
    "Campaign Performance Report": [
        "1. Executive Summary",
        "2. Campaign Objectives",
        "3. Audience & Targeting",
        "4. Channel Performance",
        "5. Key Metrics Dashboard",
        "6. Budget vs Spend",
        "7. Insights & Learnings",
        "8. Recommendations",
    ],
    "Social Media Strategy": [
        "1. Overview & Goals",
        "2. Platform Selection",
        "3. Target Audience",
        "4. Content Strategy per Platform",
        "5. Engagement Strategy",
        "6. Influencer & Partnership Strategy",
        "7. Paid Social Plan",
        "8. Success Metrics",
        "9. Tools & Workflow",
    ],
    "Press Release Template": [
        "1. Headline & Dateline",
        "2. Lead Paragraph",
        "3. Body — Key Details",
        "4. Executive Quote",
        "5. About the Company",
        "6. Media Contact",
    ],
    "Market Research Report": [
        "1. Executive Summary",
        "2. Research Objectives",
        "3. Methodology",
        "4. Market Overview",
        "5. Customer Insights",
        "6. Competitive Landscape",
        "7. Key Findings",
        "8. Conclusions & Recommendations",
    ],
    "Email Marketing Plan": [
        "1. Campaign Goals",
        "2. Target Audience & Segmentation",
        "3. Email Types & Cadence",
        "4. Content Strategy",
        "5. Automation & Drip Sequences",
        "6. A/B Testing Plan",
        "7. Success Metrics",
        "8. Compliance (GDPR/CAN-SPAM)",
    ],
    "Lead Generation Plan": [
        "1. Overview & Goals",
        "2. Target ICP",
        "3. Lead Sources",
        "4. Lead Capture Methods",
        "5. Lead Scoring Model",
        "6. Nurturing Strategy",
        "7. Sales Handoff Process",
        "8. Metrics & Conversion Goals",
    ],

    # ── QA & Testing ─────────────────────────────────────────────
    "Test Plan Document": [
        "1. Introduction & Purpose",
        "2. Scope of Testing",
        "3. Test Objectives",
        "4. Test Strategy & Approach",
        "5. Test Levels",
        "6. Test Environment Requirements",
        "7. Test Schedule & Milestones",
        "8. Resource & Responsibility Plan",
        "9. Risk & Mitigation",
        "10. Entry & Exit Criteria",
        "11. Defect Management Process",
        "12. Test Deliverables",
        "13. Approvals",
    ],
    "Test Strategy Document": [
        "1. Overview & Purpose",
        "2. Test Scope",
        "3. Testing Levels & Types",
        "4. Tools & Environments",
        "5. Entry & Exit Criteria",
        "6. Risk Management",
        "7. Roles & Responsibilities",
        "8. Metrics & Reporting",
    ],
    "Test Case Template": [
        "1. Test Case ID & Title",
        "2. Objective",
        "3. Pre-conditions",
        "4. Test Steps",
        "5. Expected Result",
        "6. Actual Result",
        "7. Status & Notes",
    ],
    "Bug Report Template": [
        "1. Bug ID & Title",
        "2. Severity & Priority",
        "3. Environment",
        "4. Steps to Reproduce",
        "5. Expected vs Actual Behavior",
        "6. Screenshots/Logs",
        "7. Assignee & Status",
    ],
    "QA Checklist": [
        "1. Functional Testing Items",
        "2. UI/UX Checks",
        "3. Performance Checks",
        "4. Security Checks",
        "5. Compatibility Checks",
        "6. Regression Items",
        "7. Release Readiness Criteria",
    ],
    "Automation Test Plan": [
        "1. Automation Objectives",
        "2. Scope of Automation",
        "3. Tool & Framework Selection",
        "4. Test Cases for Automation",
        "5. CI/CD Integration",
        "6. Execution Strategy",
        "7. Maintenance Plan",
        "8. Success Metrics",
    ],
    "Regression Test Report": [
        "1. Executive Summary", "2. Scope",
        "3. Tests Executed", "4. Pass/Fail Summary",
        "5. Defects Found", "6. Risk Areas",
        "7. Sign-Off Recommendation",
    ],
    "UAT Document": [
        "1. UAT Objectives", "2. Scope",
        "3. Participants & Roles", "4. Test Scenarios",
        "5. Test Data", "6. Entry & Exit Criteria",
        "7. Defect Log", "8. Sign-Off",
    ],
    "Performance Testing Report": [
        "1. Executive Summary",
        "2. Test Objectives & Scope",
        "3. Test Environment & Tools",
        "4. Load Test Scenarios",
        "5. Performance Metrics",
        "6. Results Analysis",
        "7. Bottlenecks & Root Causes",
        "8. Recommendations",
        "9. Benchmark Comparison",
        "10. Conclusion",
    ],
    "Test Coverage Report": [
        "1. Overview", "2. Coverage Scope",
        "3. Features Tested", "4. Coverage Percentage",
        "5. Gaps & Risks", "6. Recommendations",
    ],

    # ── Data & Analytics ─────────────────────────────────────────
    "Data Governance Policy": [
        "1. Purpose & Scope",
        "2. Data Governance Principles",
        "3. Data Governance Framework",
        "4. Roles & Responsibilities",
        "5. Data Ownership & Stewardship",
        "6. Data Classification",
        "7. Data Quality Standards",
        "8. Data Lifecycle Management",
        "9. Metadata Management",
        "10. Access & Security",
        "11. Compliance & Regulatory Requirements",
        "12. Policy Review Cycle",
    ],
    "Data Dictionary": [
        "1. Overview & Purpose",
        "2. Dataset Description",
        "3. Field Definitions & Data Types",
        "4. Primary & Foreign Keys",
        "5. Business Rules & Constraints",
        "6. Data Source & Lineage",
        "7. Update Frequency",
        "8. Data Owner & Steward",
    ],
    "Business Intelligence (BI) Report": [
        "1. Executive Summary", "2. Reporting Period",
        "3. Key Metrics Dashboard", "4. Revenue & Growth",
        "5. Operational Metrics", "6. Trend Analysis",
        "7. Insights & Anomalies", "8. Recommendations",
    ],
    "KPI Dashboard Documentation": [
        "1. Dashboard Overview", "2. KPI Definitions",
        "3. Data Sources", "4. Calculation Methodology",
        "5. Refresh Frequency", "6. Access & Permissions",
        "7. Interpretation Guide",
    ],
    "Data Pipeline Documentation": [
        "1. Pipeline Overview",
        "2. Data Sources",
        "3. Ingestion Layer",
        "4. Transformation Logic",
        "5. Loading & Storage",
        "6. Scheduling & Orchestration",
        "7. Error Handling & Alerts",
        "8. Data Quality Checks",
        "9. Tools & Technologies",
        "10. Maintenance & Support",
    ],
    "Data Quality Report": [
        "1. Executive Summary", "2. Quality Dimensions Assessed",
        "3. Data Issues Found", "4. Root Cause Analysis",
        "5. Impact Assessment", "6. Remediation Actions",
        "7. Monitoring Plan",
    ],
    "Analytics Strategy Document": [
        "1. Vision & Objectives",
        "2. Current State Assessment",
        "3. Data Maturity Model",
        "4. Target Analytics Capabilities",
        "5. Technology & Platform Roadmap",
        "6. Data Governance Integration",
        "7. Team & Skills Plan",
        "8. Use Case Prioritization",
        "9. OKRs & Success Metrics",
        "10. Implementation Roadmap",
    ],
    "Predictive Model Report": [
        "1. Executive Summary", "2. Business Problem",
        "3. Data & Features", "4. Methodology",
        "5. Model Performance", "6. Validation Results",
        "7. Limitations", "8. Deployment Plan",
        "9. Monitoring Strategy",
    ],
    "Data Privacy Impact Assessment": [
        "1. Overview & Purpose",
        "2. Data Processing Description",
        "3. Data Types & Sensitivity",
        "4. Legal Basis & Consent",
        "5. Data Flows",
        "6. Privacy Risks Identified",
        "7. Risk Mitigation Measures",
        "8. Residual Risk Assessment",
        "9. DPO Sign-Off",
    ],
    "Reporting Standards Guide": [
        "1. Purpose & Scope",
        "2. Report Structure Standards",
        "3. Visualization Guidelines",
        "4. Data Validation Rules",
        "5. Naming Conventions",
        "6. Accessibility Standards",
        "7. Review & Approval Process",
        "8. Tool-Specific Guidelines",
    ],

    # ── Platform & Infrastructure ────────────────────────────────
    "Infrastructure Architecture Document": [
        "1. Architecture Overview & Principles",
        "2. Core Infrastructure Components",
        "3. Cloud Architecture Design",
        "4. Network Architecture",
        "5. Storage Architecture",
        "6. Compute & Container Strategy",
        "7. Data Flow & Interactions",
        "8. Security Architecture",
        "9. High Availability & Redundancy",
        "10. Disaster Recovery Design",
        "11. Monitoring & Observability",
        "12. Scaling Strategy",
        "13. Cost Optimization",
    ],
    "Cloud Deployment Guide": [
        "1. Overview & Prerequisites",
        "2. Cloud Environment Setup",
        "3. Infrastructure as Code (IaC)",
        "4. CI/CD Pipeline",
        "5. Deployment Steps",
        "6. Configuration & Secrets Management",
        "7. Post-Deployment Validation",
        "8. Rollback Procedure",
        "9. Monitoring Setup",
    ],
    "Capacity Planning Report": [
        "1. Executive Summary",
        "2. Current Resource Utilization",
        "3. Growth Projections",
        "4. Capacity Gaps",
        "5. Scaling Recommendations",
        "6. Cost Projections",
        "7. Implementation Timeline",
        "8. Review Schedule",
    ],
    "Infrastructure Security Policy": [
        "1. Purpose & Scope",
        "2. Security Principles",
        "3. Network Security Controls",
        "4. Endpoint Security",
        "5. Cloud Security",
        "6. Access Controls",
        "7. Vulnerability Management",
        "8. Patch Management",
        "9. Security Monitoring",
        "10. Incident Response",
        "11. Compliance & Audit",
    ],
    "Scalability Planning Document": [
        "1. Overview & Goals",
        "2. Current Architecture Limits",
        "3. Scaling Requirements",
        "4. Horizontal vs Vertical Scaling",
        "5. Auto-Scaling Strategy",
        "6. Database Scaling",
        "7. CDN & Caching Strategy",
        "8. Load Testing Plan",
        "9. Cost Implications",
        "10. Implementation Roadmap",
    ],
    "Configuration Management Document": [
        "1. Purpose & Scope",
        "2. Configuration Items (CIs)",
        "3. Tools & Technology",
        "4. Baseline Configuration",
        "5. Change Tracking Process",
        "6. Configuration Audits",
        "7. Roles & Responsibilities",
    ],
    "SLA for Infrastructure": [
        "1. Parties & Purpose", "2. Service Scope",
        "3. Uptime Commitments", "4. Response & Resolution Times",
        "5. Monitoring & Reporting", "6. Maintenance Windows",
        "7. SLA Penalties & Credits", "8. Exclusions",
    ],
    "Uptime & Availability Report": [
        "1. Executive Summary", "2. Reporting Period",
        "3. Availability Metrics", "4. Downtime Events",
        "5. Root Cause Summary", "6. SLA Compliance",
        "7. Improvement Actions",
    ],

    # ── Partnership & Alliances ──────────────────────────────────
    "Partnership Agreement": [
        "1. Parties & Recitals",
        "2. Definitions",
        "3. Scope of Partnership",
        "4. Roles & Responsibilities",
        "5. Financial Arrangements",
        "6. Intellectual Property",
        "7. Confidentiality",
        "8. Term & Renewal",
        "9. Termination Conditions",
        "10. Dispute Resolution",
        "11. Governing Law",
        "12. General Provisions",
    ],
    "Memorandum of Understanding (MoU)": [
        "1. Parties & Background",
        "2. Purpose of MoU",
        "3. Areas of Cooperation",
        "4. Responsibilities of Each Party",
        "5. Financial Arrangements",
        "6. Confidentiality",
        "7. Duration & Renewal",
        "8. Termination",
        "9. Governing Law",
    ],
    "NDA for Partners": [
        "1. Parties", "2. Confidential Information",
        "3. Obligations", "4. Exclusions",
        "5. Duration", "6. Return of Information",
        "7. Remedies", "8. Governing Law",
    ],
    "Channel Partner Agreement": [
        "1. Parties & Definitions",
        "2. Scope & Territory",
        "3. Distribution Rights",
        "4. Partner Obligations",
        "5. Company Obligations",
        "6. Sales Targets & Incentives",
        "7. Pricing & Margins",
        "8. Training & Support",
        "9. Marketing & Co-branding",
        "10. Reporting Requirements",
        "11. Term & Termination",
        "12. Governing Law",
    ],
    "Affiliate Program Agreement": [
        "1. Parties & Program Overview",
        "2. Affiliate Obligations",
        "3. Commission Structure",
        "4. Tracking & Attribution",
        "5. Payment Terms",
        "6. Prohibited Activities",
        "7. Brand Usage",
        "8. Term & Termination",
    ],
    "Strategic Alliance Proposal": [
        "1. Executive Summary",
        "2. About Both Organizations",
        "3. Alliance Objectives",
        "4. Proposed Collaboration Activities",
        "5. Value & Benefits for Both Parties",
        "6. Governance Structure",
        "7. Timeline & Milestones",
        "8. Financial Considerations",
        "9. Risks & Mitigations",
        "10. Next Steps",
    ],
    "Partner Onboarding Guide": [
        "1. Welcome & Overview",
        "2. Onboarding Timeline",
        "3. Portal & Tool Access",
        "4. Training Program",
        "5. Co-selling Guidelines",
        "6. Marketing Resources",
        "7. Support & Escalation",
        "8. KPIs & Success Metrics",
    ],
    "Joint Marketing Plan": [
        "1. Overview & Objectives",
        "2. Target Audience",
        "3. Messaging & Positioning",
        "4. Joint Activities & Campaigns",
        "5. Channel Plan",
        "6. Budget & Cost Split",
        "7. Content & Asset Plan",
        "8. Success Metrics",
        "9. Governance & Approvals",
    ],
    "Revenue Sharing Agreement": [
        "1. Parties", "2. Revenue Sources",
        "3. Revenue Split Structure", "4. Calculation Method",
        "5. Payment Schedule", "6. Reporting Requirements",
        "7. Audit Rights", "8. Governing Law",
    ],
    "Partner Performance Report": [
        "1. Executive Summary", "2. Reporting Period",
        "3. KPI Performance", "4. Revenue Contribution",
        "5. Activity Summary", "6. Achievements",
        "7. Improvement Areas", "8. Next Period Plan",
    ],
}

DEFAULT_SECTIONS = [
    "1. Executive Summary", "2. Purpose & Scope",
    "3. Background & Context", "4. Key Details & Procedures",
    "5. Roles & Responsibilities", "6. Standards & Compliance",
    "7. Implementation Guidelines", "8. Review & Update Cycle",
]


# ══════════════════════════════════════════════════════════════════════
# DEPARTMENT TONE
# ══════════════════════════════════════════════════════════════════════

DEPARTMENT_TONE = {
    "HR & People Operations": "professional, empathetic, and clear. Use plain English. Follow employment law best practices.",
    "Legal & Compliance": "precise, formal, and legally sound. Use defined terms. Avoid ambiguity. Include clause numbering.",
    "Engineering & Operations": "technical, structured, and implementation-focused. Include step-by-step procedures and specific commands.",
    "IT & Internal Systems": "clear, technical, and policy-oriented. Reference ISO 27001, NIST, SOC 2 where applicable.",
    "Security & Information Assurance": "formal, risk-aware, and methodical. Reference NIST, ISO 27001, OWASP. Use CVSS scoring conventions.",
    "Finance & Operations": "analytical, precise, and data-driven. Include financial terminology and structured tables.",
    "Sales & Customer Facing": "professional yet persuasive. Focus on value delivery and client outcomes.",
    "Product & Design": "clear, user-focused, and outcome-oriented. Use jobs-to-be-done framing.",
    "Marketing & Content": "engaging, brand-aligned, and data-informed. Balance creativity with measurable KPIs.",
    "Data & Analytics": "analytical and methodology-driven. Reference data quality dimensions and BI best practices.",
    "QA & Testing": "systematic and process-oriented. Follow IEEE 829 standards. Use structured test terminology.",
    "Partnership & Alliances": "collaborative, strategic, and professional. Balance legal precision with relationship language.",
    "Platform & Infrastructure Operations": "technical and reliability-focused. Reference SRE practices, SLO/SLA terminology.",
}


# ══════════════════════════════════════════════════════════════════════
# SMART DEFAULTS
# ══════════════════════════════════════════════════════════════════════

SMART_DEFAULTS = {
    "document_version": "1.0",
    "effective_date": date.today().strftime("%Y-%m-%d"),
    "work_policy": "Hybrid",
    "it_environment": "Hybrid",
    "deployment_environment": "Production",
    "security_standard": "ISO 27001",
    "security_framework": "ISO 27001",
    "currency": "USD",
    "uptime_commitment": "99.9%",
    "probation_period": "3",
    "annual_leave_days": "21",
    "bug_severity": "Medium",
    "approval_status": "Pending",
    "testing_environment": "QA",
    "product_stage": "Production",
    "pricing_model": "Subscription",
    "contract_type": "Full-Time",
    "partnership_type": "Strategic Alliance",
    "cloud_provider": "AWS",
    "data_platform": "Snowflake",
    "deployment_model": "Multi Region",
    "research_method": "User Interviews",
    "feedback_source": "Survey",
    "authentication_method": "OAuth2",
    "crm_system": "Salesforce",
    "wireframe_tool": "Figma",
}


# ══════════════════════════════════════════════════════════════════════
# STREAMLIT QUESTION RENDERER
# ══════════════════════════════════════════════════════════════════════

def render_question(q, key_prefix=""):
    """Render a single question widget. Returns the value."""
    qid = q["id"]
    label = q["question"]
    qtype = q.get("type", "text")
    required = q.get("required", False)
    options = q.get("options", [])
    key = f"{key_prefix}_{qid}"
    label_display = f"{label} {'*' if required else ''}"
    default = SMART_DEFAULTS.get(qid, "")

    if qtype == "text":
        val = st.text_input(label_display, key=key,
                            placeholder=f"e.g. {default}" if default else "")
    elif qtype == "textarea":
        val = st.text_area(label_display, key=key, height=100,
                           placeholder="Enter details here...")
    elif qtype == "number":
        val = st.number_input(
            label_display, key=key, min_value=0,
            value=int(default) if default and str(default).isdigit() else 0
        )
    elif qtype == "date":
        default_date = date.today()
        if default:
            try:
                default_date = datetime.strptime(default, "%Y-%m-%d").date()
            except Exception:
                pass
        val = st.date_input(label_display, key=key, value=default_date)
    elif qtype == "select":
        opts = options if options else [default]
        idx = opts.index(default) if default in opts else 0
        val = st.selectbox(label_display, options=opts, index=idx, key=key)
    elif qtype == "multi_select":
        val = st.multiselect(label_display, options=options, key=key)
    else:
        val = st.text_input(label_display, key=key)

    return val


def render_document_questions(department_data, doc_type, key_prefix="qa"):
    """
    Render all questions for a document and return collected answers.
    Returns dict with keys: common, metadata, document, all
    """
    common_answers = {}
    metadata_answers = {}
    doc_answers = {}
    department = department_data.get("department", "")

    with st.expander("📋 Document Metadata", expanded=True):
        st.caption("Document control information.")
        cols = st.columns(2)
        for i, q in enumerate(department_data.get("metadata_questions", [])):
            with cols[i % 2]:
                metadata_answers[q["id"]] = render_question(
                    q, key_prefix=f"{key_prefix}_meta"
                )

    with st.expander(f"🏢 {department} — Company Context", expanded=True):
        st.caption("Background context about your organization.")
        for q in department_data.get("common_questions", []):
            common_answers[q["id"]] = render_question(
                q, key_prefix=f"{key_prefix}_common"
            )

    doc_questions = department_data.get("document_questions", {}).get(doc_type, [])
    if doc_questions:
        with st.expander(f"📝 {doc_type} — Specific Details", expanded=True):
            st.caption(
                "Personalize your document. "
                "Leave blank to auto-generate with best-practice content."
            )
            for q in doc_questions:
                doc_answers[q["id"]] = render_question(
                    q, key_prefix=f"{key_prefix}_doc"
                )

    all_answers = {**common_answers, **doc_answers}

    return {
        "common": common_answers,
        "metadata": metadata_answers,
        "document": doc_answers,
        "all": all_answers,
    }


# ══════════════════════════════════════════════════════════════════════
# PROFESSIONAL PROMPT BUILDER
# ══════════════════════════════════════════════════════════════════════

def build_professional_prompt(department, doc_type, user_answers, metadata=None):
    """
    Build a complete professional AI prompt.
    Automatically controls document length based on doc type.
    """
    today = date.today().strftime("%Y-%m-%d")
    tone = DEPARTMENT_TONE.get(department, "professional, clear, and thorough")
    sections = DOCUMENT_SECTIONS.get(doc_type, DEFAULT_SECTIONS)
    length_key = DOCUMENT_LENGTH.get(doc_type, "medium")
    length_instruction = LENGTH_INSTRUCTIONS[length_key]

    # Get exact page/word targets from DOCUMENT_SPECS
    specs = DOCUMENT_SPECS.get(doc_type, {})
    min_pages = specs.get("min_pages", "")
    max_pages = specs.get("max_pages", "")
    target_words = specs.get("target_words", "")
    if specs:
        page_target = (
            f"STRICT LENGTH: {min_pages}-{max_pages} pages / ~{target_words} words. "
            f"Do NOT exceed or fall short of this range."
        )
    else:
        page_target = ""

    meta = metadata or {}
    doc_title = meta.get("document_title") or doc_type
    author = meta.get("author_name") or "Document Owner"
    approved_by = meta.get("approved_by") or "Senior Management"
    reviewed_by = meta.get("reviewed_by") or approved_by
    version = meta.get("document_version") or "1.0"
    eff_date = meta.get("effective_date") or today
    if hasattr(eff_date, "strftime"):
        eff_date = eff_date.strftime("%Y-%m-%d")

    filled = {
        k: str(v).strip()
        for k, v in user_answers.items()
        if v and str(v).strip() not in ("", "None", "null", "0", "[]")
    }

    if filled:
        context_lines = [
            f"- **{k.replace('_', ' ').title()}**: {v}"
            for k, v in filled.items()
        ]
        context_block = "\n".join(context_lines)
    else:
        context_block = "- No specific context provided — generate using industry best practices."

    sections_block = "\n".join(f"  {s}" for s in sections)

    prompt = (
        f"You are a senior {department} specialist and professional technical writer "
        f"with 15+ years of enterprise documentation experience.\n\n"
        f"Generate a **complete, accurate, publication-ready {doc_type}** document.\n\n"
        f"---\n\n"
        f"## Document Metadata\n\n"
        f"| Attribute      | Details                  |\n"
        f"|----------------|--------------------------|\n"
        f"| Document Title | {doc_title}              |\n"
        f"| Document Type  | {doc_type}               |\n"
        f"| Department     | {department}             |\n"
        f"| Version        | {version}                |\n"
        f"| Effective Date | {eff_date}               |\n"
        f"| Author         | {author}                 |\n"
        f"| Reviewed By    | {reviewed_by}            |\n"
        f"| Approved By    | {approved_by}            |\n"
        f"| Classification | Internal — Confidential  |\n\n"
        f"---\n\n"
        f"## Context Provided\n\n"
        f"{context_block}\n\n"
        f"---\n\n"
        f"## Generation Instructions\n\n"
        f"### 1. Length & Depth\n"
        f"{length_instruction}\n"
        f"{page_target}\n\n"
        f"### 2. Tone & Style\n"
        f"Write in a style that is: **{tone}**\n"
        f"- Formal, professional language throughout\n"
        f"- Specific and actionable — no vague filler text\n"
        f"- Industry-standard terminology for **{department}**\n"
        f"- Written as if reviewed by senior leadership or an external auditor\n\n"
        f"### 3. Required Sections\n"
        f"Generate ALL sections below with complete, substantive content:\n\n"
        f"{sections_block}\n\n"
        f"### 4. Auto-Fill Rules\n"
        f"- Missing section details → generate professional industry-standard content\n"
        f"- NEVER write 'Not provided', 'TBD', or 'N/A'\n"
        f"- Missing company values → use realistic bracketed placeholders: [Company Name], [Manager Name]\n"
        f"- Apply standards automatically: ISO 27001, NIST, GDPR, SOC 2, IEEE 829, OWASP\n\n"
        f"### 5. Formatting\n"
        f"- Title: # {doc_title}\n"
        f"- Major sections: ##\n"
        f"- Sub-sections: ###\n"
        f"- Use markdown tables for structured data\n"
        f"- Numbered lists for sequential steps\n"
        f"- Bullet points for non-sequential items\n"
        f"- Divider --- between major sections\n"
        f"- End with ## Document Control table:\n\n"
        f"| Version | Date | Author | Changes |\n"
        f"|---------|------|--------|---------|\n"
        f"| {version} | {eff_date} | {author} | Initial release |\n\n"
        f"---\n\n"
        f"Output ONLY the document. No preamble, no commentary."
    )

    return prompt


# ══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════

def get_department_data(all_departments, department_name):
    """Find department config by name."""
    for dept in all_departments:
        if dept.get("department") == department_name:
            return dept
    return {}


def get_all_doc_types(department_data):
    """Return list of document types for a department."""
    return list(department_data.get("document_questions", {}).keys())


def get_all_departments(all_departments):
    """Return list of all department names."""
    return [d.get("department", "") for d in all_departments]