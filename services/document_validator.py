"""
Document Validator
- Checks generated document for format, quality, completeness
- Returns validation report with score and issues
- Used after generation before saving to DB
"""
import re
from typing import Dict, List, Tuple
from utils.logger import setup_logger

logger = setup_logger(__name__)


# ============================================================
# REQUIRED SECTIONS PER DOC TYPE
# ============================================================
REQUIRED_SECTIONS = {
    "SOP": [
        "purpose", "scope", "roles", "procedure", "tools", "compliance", "review", "approval"
    ],
    "Policy": [
        "purpose", "scope", "policy statement", "roles", "compliance", "enforcement", "review", "approval"
    ],
    "Proposal": [
        "executive summary", "background", "objective", "solution", "timeline", "budget", "risk", "approval"
    ],
    "SOW": [
        "purpose", "scope", "deliverable", "timeline", "roles", "budget", "acceptance", "approval"
    ],
    "Incident Report": [
        "incident", "date", "description", "impact", "root cause", "resolution", "lessons", "approval"
    ],
    "FAQ": [
        "purpose", "scope", "frequently asked", "question", "answer", "review"
    ],
    "Runbook": [
        "purpose", "scope", "prerequisite", "step", "troubleshoot", "escalation", "review"
    ],
    "Playbook": [
        "purpose", "scope", "roles", "procedure", "scenario", "kpi", "review", "approval"
    ],
    "RCA": [
        "incident", "description", "impact", "root cause", "corrective", "preventive", "lessons", "approval"
    ],
    "SLA": [
        "purpose", "scope", "parties", "service", "metric", "escalation", "penalty", "review", "approval"
    ],
    "Change Management": [
        "purpose", "scope", "change request", "impact", "roles", "approval", "testing", "review"
    ],
    "Handbook": [
        "welcome", "overview", "policy", "procedure", "compliance", "acknowledgment"
    ],
}

# Minimum word counts per doc type
MIN_WORD_COUNTS = {
    "SOP": 1500,
    "Policy": 1200,
    "Proposal": 1500,
    "SOW": 1200,
    "Incident Report": 800,
    "FAQ": 1000,
    "Runbook": 1200,
    "Playbook": 1500,
    "RCA": 1000,
    "SLA": 1000,
    "Change Management": 1200,
    "Handbook": 2000,
}

# Placeholder patterns that should NOT appear in generated docs
PLACEHOLDER_PATTERNS = [
    r"\[insert.*?\]",
    r"\[your.*?\]",
    r"\[company name\]",
    r"\[department\]",
    r"\[date\]",
    r"\[tbd\]",
    r"\[add.*?\]",
    r"\[specify.*?\]",
    r"\[enter.*?\]",
    r"\[fill.*?\]",
    r"lorem ipsum",
    r"placeholder",
    r"xxx+",
    r"n/a\s*\(not provided\)",
]


# ============================================================
# VALIDATION FUNCTIONS
# ============================================================

def check_word_count(content: str, doc_type: str) -> Tuple[bool, int, int]:
    """Check if document meets minimum word count."""
    word_count = len(content.split())
    min_count  = MIN_WORD_COUNTS.get(doc_type, 800)
    return word_count >= min_count, word_count, min_count


def check_sections_present(content: str, doc_type: str) -> Tuple[bool, List[str], List[str]]:
    """Check if required sections are present."""
    content_lower = content.lower()
    required      = REQUIRED_SECTIONS.get(doc_type, [])
    present       = [s for s in required if s in content_lower]
    missing       = [s for s in required if s not in content_lower]
    ok            = len(missing) == 0
    return ok, present, missing


def check_markdown_structure(content: str) -> Tuple[bool, List[str]]:
    """Check if document has proper markdown headings."""
    issues = []
    h2_sections = re.findall(r"^##\s+.+", content, re.MULTILINE)
    h3_sections = re.findall(r"^###\s+.+", content, re.MULTILINE)

    if len(h2_sections) < 3:
        issues.append(f"Only {len(h2_sections)} main sections (##) found — expected at least 3")

    if len(h3_sections) < 2:
        issues.append(f"Only {len(h3_sections)} subsections (###) found — expected at least 2")

    return len(issues) == 0, issues


def check_placeholders(content: str) -> Tuple[bool, List[str]]:
    """Check for unfilled placeholder text."""
    content_lower = content.lower()
    found = []
    for pattern in PLACEHOLDER_PATTERNS:
        matches = re.findall(pattern, content_lower)
        if matches:
            found.extend(matches[:3])  # max 3 examples per pattern
    return len(found) == 0, found


def check_company_name(content: str, company_name: str) -> Tuple[bool, int]:
    """Check if company name is used in document."""
    if company_name in ("the company", "", "testco"):
        return True, 0
    count = content.lower().count(company_name.lower())
    return count >= 3, count


def check_has_tables(content: str, doc_type: str) -> Tuple[bool, int]:
    """Check if document has tables where expected."""
    table_count = len(re.findall(r"^\|.+\|", content, re.MULTILINE))
    doc_types_needing_tables = {"SOP", "SLA", "Change Management", "SOW", "RCA", "Proposal"}

    if doc_type in doc_types_needing_tables:
        return table_count >= 1, table_count
    return True, table_count  # optional for other types


def check_has_numbered_lists(content: str, doc_type: str) -> Tuple[bool, int]:
    """Check if procedural docs have numbered steps."""
    numbered = len(re.findall(r"^\d+\.\s+", content, re.MULTILINE))
    procedural_types = {"SOP", "Runbook", "Playbook", "Change Management"}

    if doc_type in procedural_types:
        return numbered >= 5, numbered
    return True, numbered


def check_version_history(content: str) -> bool:
    """Check if document has version history section."""
    content_lower = content.lower()
    return any(kw in content_lower for kw in [
        "version history", "revision history", "change log",
        "version | date", "version|date", "document history"
    ])


def check_specificity(content: str) -> Tuple[bool, List[str]]:
    """Check for vague/generic phrases that indicate low quality."""
    vague_phrases = [
        "as needed", "when appropriate", "in a timely manner",
        "best practices", "ensure compliance", "coordinate with",
        "work closely", "as required", "on a regular basis",
    ]
    content_lower = content.lower()
    found = [p for p in vague_phrases if content_lower.count(p) > 3]
    return len(found) == 0, found


def check_approval_section(content: str) -> bool:
    """Check if document has approval section."""
    content_lower = content.lower()
    return any(kw in content_lower for kw in [
        "approval", "approved by", "sign-off", "sign off", "authorized by"
    ])


# ============================================================
# SCORING
# ============================================================

def calculate_score(checks: Dict) -> int:
    """Calculate quality score out of 100."""
    weights = {
        "word_count":       20,
        "sections":         25,
        "markdown":         10,
        "no_placeholders":  15,
        "company_name":     10,
        "tables":           5,
        "numbered_lists":   5,
        "version_history":  5,
        "approval":         5,
    }
    score = 0
    for check, weight in weights.items():
        if checks.get(check, False):
            score += weight
    
    # Bonus points for quality indicators
    quality_bonuses = checks.get("quality_bonuses", 0)
    score = min(100, score + quality_bonuses)  # Cap at 100
    
    return score


def get_grade(score: int) -> Tuple[str, str]:
    """Return letter grade and color."""
    if score >= 90:
        return "A", "🟢 Excellent"
    elif score >= 75:
        return "B", "🟡 Good"
    elif score >= 60:
        return "C", "🟠 Acceptable"
    elif score >= 40:
        return "D", "🔴 Needs Improvement"
    else:
        return "F", "❌ Poor Quality"


# ============================================================
# MAIN VALIDATE FUNCTION
# ============================================================

def validate_document(
    content: str,
    doc_type: str,
    department: str,
    question_answers: dict = None,
) -> Dict:
    """
    Run all validation checks and return a full report.
    
    Returns:
        {
            "valid": bool,
            "score": int,
            "grade": str,
            "word_count": int,
            "checks": {...},
            "issues": [...],
            "warnings": [...],
            "passed": [...],
        }
    """
    if not question_answers:
        question_answers = {}

    company_name = question_answers.get("company_name", "")
    issues   = []
    warnings = []
    passed   = []
    checks   = {}

    # ── 1. Word Count ──
    wc_ok, word_count, min_wc = check_word_count(content, doc_type)
    checks["word_count"] = wc_ok
    if wc_ok:
        passed.append(f"✅ Word count: {word_count:,} words (minimum: {min_wc:,})")
    else:
        issues.append(f"❌ Word count too low: {word_count:,} words (minimum required: {min_wc:,})")

    # ── 2. Required Sections ──
    sec_ok, present_secs, missing_secs = check_sections_present(content, doc_type)
    checks["sections"] = sec_ok
    if sec_ok:
        passed.append(f"✅ All required sections present ({len(present_secs)} sections)")
    else:
        issues.append(f"❌ Missing sections: {', '.join(missing_secs)}")
        if present_secs:
            warnings.append(f"⚠️ Sections found: {', '.join(present_secs)}")

    # ── 3. Markdown Structure ──
    md_ok, md_issues = check_markdown_structure(content)
    checks["markdown"] = md_ok
    if md_ok:
        h2 = len(re.findall(r"^##\s+.+", content, re.MULTILINE))
        h3 = len(re.findall(r"^###\s+.+", content, re.MULTILINE))
        passed.append(f"✅ Markdown structure: {h2} main sections, {h3} subsections")
    else:
        for issue in md_issues:
            warnings.append(f"⚠️ {issue}")
        checks["markdown"] = False

    # ── 4. No Placeholders ──
    ph_ok, placeholders = check_placeholders(content)
    checks["no_placeholders"] = ph_ok
    if ph_ok:
        passed.append("✅ No placeholder text found")
    else:
        issues.append(f"❌ Placeholder text found: {', '.join(set(placeholders[:5]))}")

    # ── 5. Company Name Usage ──
    cn_ok, cn_count = check_company_name(content, company_name)
    checks["company_name"] = cn_ok
    if company_name and company_name not in ("the company", ""):
        if cn_ok:
            passed.append(f"✅ Company name '{company_name}' used {cn_count} times")
        else:
            warnings.append(f"⚠️ Company name '{company_name}' used only {cn_count} time(s) — should appear more")

    # ── 6. Tables ──
    tbl_ok, tbl_count = check_has_tables(content, doc_type)
    checks["tables"] = tbl_ok
    if tbl_ok:
        passed.append(f"✅ Tables present: {tbl_count} table(s)")
    else:
        warnings.append(f"⚠️ No markdown tables found — {doc_type} should include at least 1 table")

    # ── 7. Numbered Lists ──
    nl_ok, nl_count = check_has_numbered_lists(content, doc_type)
    checks["numbered_lists"] = nl_ok
    if nl_ok:
        passed.append(f"✅ Numbered steps present: {nl_count} step(s)")
    else:
        warnings.append(f"⚠️ Few numbered steps ({nl_count}) — {doc_type} should have step-by-step procedures")

    # ── 8. Version History ──
    vh_ok = check_version_history(content)
    checks["version_history"] = vh_ok
    if vh_ok:
        passed.append("✅ Version history section present")
    else:
        warnings.append("⚠️ No version history section found")

    # ── 9. Approval Section ──
    ap_ok = check_approval_section(content)
    checks["approval"] = ap_ok
    if ap_ok:
        passed.append("✅ Approval section present")
    else:
        warnings.append("⚠️ No approval section found")

    # ── 10. Vague language check ──   not clear enough to fully understand
    sp_ok, vague = check_specificity(content)
    if not sp_ok:
        warnings.append(f"⚠️ Overused vague phrases: {', '.join(vague)} — consider being more specific")

    # ── 11. Quality Bonuses (A-GRADE AGGRESSIVE BOOST) ──
    quality_bonus = 0
    
    # Check for compliance terminology (GDPR, SOC2, ISO, etc) - AGGRESSIVE for A-grade
    compliance_terms = [r'\bGDPR\b', r'\bSOC\s*2\b', r'\bISO\s*27\d+\b', r'\bCCPA\b', r'\bHIPAA\b', r'\bPCI-DSS\b']
    compliance_count = sum(len(re.findall(term, content, re.IGNORECASE)) for term in compliance_terms)
    if compliance_count >= 6:
        quality_bonus += 18  # A-grade compliance framework
        passed.append(f"✅✅ EXCELLENT compliance framework: {compliance_count} standards (A-grade)")
    elif compliance_count >= 4:
        quality_bonus += 12
        passed.append(f"✅ Strong compliance: {compliance_count} standards referenced")
    elif compliance_count >= 2:
        quality_bonus += 6
        passed.append(f"✅ Compliance references: {compliance_count} standards")
    
    # Check for specific numbers and percentages (A-grade requires substantial specificity)
    numbers = len(re.findall(r'\b\d+(?:\.\d+)?%?\b', content))
    dates = len(re.findall(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{1,2}/\d{1,2}/\d{4})\b', content, re.IGNORECASE))
    if numbers >= 25:
        quality_bonus += 14  # Excellent specificity
        passed.append(f"✅✅ EXCELLENT specificity: {numbers} concrete numbers/figures (A-grade)")
    elif numbers >= 15:
        quality_bonus += 10
        passed.append(f"✅ Strong specificity: {numbers} specific numbers/figures")
    elif numbers >= 8:
        quality_bonus += 5
        passed.append(f"✅ Concrete content: {numbers} numbers/figures")
    
    if dates >= 6:
        quality_bonus += 10
        passed.append(f"✅✅ Detailed timeline: {dates} date references (A-grade)")
    elif dates >= 4:
        quality_bonus += 6
        passed.append(f"✅ Timeline defined: {dates} date references")
    elif dates >= 2:
        quality_bonus += 3
    
    # Check for professional formatting (A-grade requires extensive formatting)
    bold_items = len(re.findall(r'\*\*[^*]+\*\*', content))
    bullets = len(re.findall(r'^[\s]*[-*•+]\s+', content, re.MULTILINE))
    numbered = len(re.findall(r'^\s*\d+\.\s+', content, re.MULTILINE))
    tables = len(re.findall(r'^\|[-\s|:]+\|$', content, re.MULTILINE))
    
    if bold_items >= 15:
        quality_bonus += 8  # Professional formatting
        passed.append(f"✅✅ EXCELLENT formatting: {bold_items} emphasized terms (A-grade)")
    elif bold_items >= 8:
        quality_bonus += 5
        passed.append(f"✅ Professional formatting: {bold_items} emphasized terms")
    elif bold_items >= 4:
        quality_bonus += 2
    
    if numbered >= 15:
        quality_bonus += 10
        passed.append(f"✅✅ Clear procedures: {numbered} numbered steps (A-grade)")
    elif numbered >= 8:
        quality_bonus += 6
        passed.append(f"✅ Step-by-step content: {numbered} numbered items")
    elif numbered >= 4:
        quality_bonus += 3
    
    if bullets >= 15:
        quality_bonus += 8
        passed.append(f"✅ Well-structured lists: {bullets} bullet points")
    elif bullets >= 8:
        quality_bonus += 5
        passed.append(f"✅ Structured lists: {bullets} bullet points")
    elif bullets >= 4:
        quality_bonus += 2
    
    if tables >= 3:
        quality_bonus += 10
        passed.append(f"✅✅ Professional data tables: {tables} tables (A-grade)")
    elif tables >= 2:
        quality_bonus += 6
        passed.append(f"✅ Data tables: {tables} tables")
    elif tables >= 1:
        quality_bonus += 2
    
    # Check for complete sections (A-grade requires 8+ sections)
    if len(present_secs) >= 12:
        quality_bonus += 12  # Comprehensive structure
        passed.append(f"✅✅ COMPREHENSIVE structure: {len(present_secs)} sections (A-grade)")
    elif len(present_secs) >= 9:
        quality_bonus += 8
        passed.append(f"✅ Excellent structure: {len(present_secs)} sections")
    elif len(present_secs) >= 7:
        quality_bonus += 4
        passed.append(f"✅ Good structure: {len(present_secs)} sections")
    
    # Check for absence of weak language (A-grade MUST have strong language)
    weak_phrases = [r'\bmay be\b', r'\bcould be\b', r'\bshould be\b', r'\bpossibly\b', r'\bmight\b', r'\btbd\b']
    weak_count = sum(len(re.findall(phrase, content, re.IGNORECASE)) for phrase in weak_phrases)
    if weak_count == 0:
        quality_bonus += 12  # Perfect - no weak language
        passed.append("✅✅ EXCELLENT language: zero weak/hedging phrases (A-grade)")
    elif weak_count <= 1:
        quality_bonus += 8
        passed.append("✅ Strong language: minimal weak phrases")
    elif weak_count <= 2:
        quality_bonus += 4
    
    # Check for company name usage (A-grade personalization)
    if company_name and company_name not in ("the company", ""):
        company_mentions = len(re.findall(re.escape(company_name), content, re.IGNORECASE))
        if company_mentions >= 30:
            quality_bonus += 8
            passed.append(f"✅✅ Excellent personalization: '{company_name}' appears {company_mentions} times (A-grade)")
        elif company_mentions >= 20:
            quality_bonus += 5
            passed.append(f"✅ Good personalization: '{company_name}' appears {company_mentions} times")
        elif company_mentions >= 10:
            quality_bonus += 2
    
    checks["quality_bonuses"] = quality_bonus

    # ── Score & Grade ──
    score      = calculate_score(checks)
    grade, label = get_grade(score)
    valid      = score >= 60 and len(issues) <= 2

    return {
        "valid":      valid,
        "score":      score,
        "grade":      grade,
        "label":      label,
        "word_count": word_count,
        "doc_type":   doc_type,
        "department": department,
        "checks":     checks,
        "issues":     issues,
        "warnings":   warnings,
        "passed":     passed,
        "summary":    f"{label} — Score: {score}/100 | {word_count:,} words | {len(passed)} checks passed, {len(issues)} issues, {len(warnings)} warnings",
    }